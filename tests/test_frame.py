from gesture_mouse.frame import FrameLogic
from gesture_mouse.safety import Controller, LogActions, LogMouse
from tests.fixtures import call_pose, fist, ok_sign, open_palm, pinch, point_index, scroll_pose, shift


def setup(enabled=True):
    m = LogMouse(); c = Controller(m); f = FrameLogic(c, (1000, 800), LogActions())
    if enabled:
        f.toggle(0.0)
    return m, c, f


def buttons(m):
    return [x for x in m.calls if x[0] == "button"]


def test_preview_by_default_sends_nothing():
    m, c, f = setup(enabled=False)
    for i in range(30):
        f.step(point_index(), i / 30)
    assert m.calls == [] and not c.enabled


def test_fist_hold_toggles_and_flicker_does_not_retoggle():
    m, c, f = setup(enabled=False)
    for i in range(21):
        f.step(fist(), i / 10)
    assert c.enabled
    f.step(point_index(), 2.15)                # one noisy frame
    for i in range(30):
        f.step(fist(), 2.2 + i / 10)
    assert c.enabled


def test_open_palm_no_longer_toggles():
    m, c, f = setup(enabled=False)
    for i in range(40):
        f.step(open_palm(), i / 10)
    assert not c.enabled


def test_hand_lost_turns_off_and_stays_off():
    m, c, f = setup()
    f.step(pinch(0.1), 0.0); f.step(pinch(0.5), 0.1); f.step(pinch(0.1), 0.5)
    assert c.button_down
    assert f.step(None, 0.6) == "OFF: hand lost"
    assert buttons(m)[-1] == ("button", False) and not c.enabled
    n = len(m.calls)
    for i in range(10):
        f.step(point_index(), 1 + i / 10)
    assert len(m.calls) == n


def test_toggle_while_pinching_does_not_click():
    m, c, f = setup(enabled=False)
    f.step(pinch(0.1), 0.0)
    f.toggle(0.1)
    for i in range(10):
        f.step(pinch(0.1), 0.2 + i / 10)
    assert buttons(m) == []


def test_scroll_pose_flicker_during_drag_keeps_button():
    m, c, f = setup()
    f.step(pinch(0.5), 0.0); f.step(pinch(0.1), 0.1)
    assert buttons(m) == [("button", True)]
    held = scroll_pose(); held[4] = pinch(0.1)[4]  # middle finger flicks open while still pinching
    f.step(held, 0.2)
    f.step(pinch(0.1), 0.3)
    assert buttons(m) == [("button", True)] and c.button_down
    f.step(pinch(0.5), 0.4)                         # open fingers: drag ends normally
    assert buttons(m) == [("button", True), ("button", False)]


def test_cursor_frozen_while_closing_pinch():
    m, c, f = setup()
    f.step(pinch(0.5), 0.0)
    moves = len([x for x in m.calls if x[0] == "move"])
    f.step(shift(pinch(0.3), 0.05, 0.0), 0.1)     # closing in on a click, fingertip drifts
    assert len([x for x in m.calls if x[0] == "move"]) == moves


def test_drag_moves_cursor_while_pressed():
    m, c, f = setup()
    f.step(pinch(0.5), 0.0); f.step(pinch(0.1), 0.1)
    n = len(m.calls)
    f.step(shift(pinch(0.1), 0.1, 0.0), 0.2)
    assert m.calls[n:] and m.calls[n][0] == "move"


def test_scroll_up():
    m, c, f = setup()
    f.step(scroll_pose(), 0.0)
    f.step(shift(scroll_pose(), 0.0, -0.05), 0.1)
    assert [x for x in m.calls if x[0] == "scroll"] and m.calls[-1][1] > 0


def acts(f):
    return f.actions.calls


def test_still_palm_opens_youtube_once():
    m, c, f = setup()
    for i in range(40):
        f.step(open_palm(), i / 10)
    assert acts(f) == ["open_youtube"]
    assert not [x for x in m.calls if x[0] == "move"]   # palm never drives the cursor


def test_palm_swipe_left_next_right_prev_without_opening_youtube():
    m, c, f = setup()
    for i in range(8):
        f.step(shift(open_palm(), -0.04 * i, 0), i / 30)
    for i in range(30):                                   # palm stays up after the swipe
        f.step(shift(open_palm(), -0.28, 0), (8 + i) / 30 + 0.5)
    for i in range(8):
        f.step(shift(open_palm(), -0.28 + 0.04 * i, 0), 3 + i / 30)
    assert acts(f) == ["next_video", "prev_video"]


def test_call_pose_starts_voice_search_once():
    m, c, f = setup()
    for i in range(20):
        f.step(call_pose(), i / 10)
    assert acts(f) == ["voice_search"]


def test_no_actions_while_control_off():
    m, c, f = setup(enabled=False)
    for i in range(30):
        f.step(open_palm(), i / 10)
    for i in range(20):
        f.step(call_pose(), 3 + i / 10)
    assert acts(f) == [] and m.calls == []


def test_ok_sign_clicks():
    m, c, f = setup()
    f.step(pinch(0.5), 0.0); f.step(ok_sign(), 0.1)
    assert buttons(m) == [("button", True)]
