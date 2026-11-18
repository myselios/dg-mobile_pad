from gesture_mouse.remote_logic import RemoteHandler
from gesture_mouse.safety import Controller, LogActions, LogMouse


def setup(pos=(500, 400), on=True):
    m = LogMouse(); c = Controller(m); a = LogActions()
    h = RemoteHandler(c, a, (1000, 800), lambda: pos)
    if on:
        h.handle({"t": "on"})
    return m, c, a, h


def test_starts_off_until_on():
    m, c, a, h = setup(on=False)
    h.handle({"t": "move", "dx": 10, "dy": 0}); h.handle({"t": "click"})
    assert m.calls == [] and not c.enabled


def test_move_is_relative_to_current_cursor():
    m, c, a, h = setup()
    h.handle({"t": "move", "dx": 1, "dy": -1})
    (_, x, y), = m.calls
    assert x > 500 and y < 400


def test_fast_moves_accelerate():
    _, _, _, h = setup()
    slow = h.target(0, 0, 2, 0)[0]
    fast = h.target(0, 0, 20, 0)[0]
    assert fast > 10 * slow


def test_move_clamps_to_screen():
    m, c, a, h = setup(pos=(995, 5))
    h.handle({"t": "move", "dx": 50, "dy": -50})
    assert m.calls[-1] == ("move", 999, 0)


def test_click_and_right_click():
    m, c, a, h = setup()
    h.handle({"t": "click"}); h.handle({"t": "right"})
    assert m.calls == [("button", True), ("button", False), ("right",)]


def test_drag_down_move_up():
    m, c, a, h = setup()
    h.handle({"t": "down"}); h.handle({"t": "move", "dx": 5, "dy": 0}); h.handle({"t": "up"})
    assert [x[0] for x in m.calls] == ["button", "move", "button"] and not c.button_down


def test_scroll_natural_direction():
    m, c, a, h = setup()
    h.handle({"t": "scroll", "dy": -10})          # finger moves up -> content moves up (scroll down)
    assert m.calls[-1][0] == "scroll" and m.calls[-1][1] < 0


def test_actions_only_when_on_and_whitelisted():
    m, c, a, h = setup()
    h.handle({"t": "action", "name": "next_video"})
    h.handle({"t": "action", "name": "__init__"})
    h.handle({"t": "off"}); h.handle({"t": "action", "name": "prev_video"})
    assert a.calls == ["next_video"]


def test_off_releases_held_button():
    m, c, a, h = setup()
    h.handle({"t": "down"}); h.handle({"t": "off"})
    assert m.calls[-1] == ("button", False) and not c.enabled


def test_disconnect_releases_and_disables():
    m, c, a, h = setup()
    h.handle({"t": "down"}); h.disconnected()
    assert m.calls[-1] == ("button", False) and not c.enabled and not c.button_down


def test_rejects_bad_input():
    m, c, a, h = setup()
    for bad in [{"t": "move", "dx": float("nan"), "dy": 0}, {"t": "move", "dx": "1", "dy": 0},
                {"t": "move", "dx": 1e9, "dy": 0}, {"t": "nope"}, {"x": 1}, "not a dict"]:
        assert h.handle(bad) == "bad message"
    assert m.calls == []
