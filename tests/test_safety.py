from gesture_mouse.safety import Controller, LogMouse, cleanup


def on():
    m = LogMouse(); c = Controller(m); c.toggle()
    return m, c


def test_starts_disabled_and_sends_nothing():
    m = LogMouse(); c = Controller(m)
    c.move(1, 1); c.press(); c.scroll(3)
    assert m.calls == [] and not c.enabled


def test_hand_lost_releases_then_disables():
    m, c = on(); c.press(); c.hand_lost()
    assert m.calls == [("button", True), ("button", False)]
    assert not c.enabled and not c.button_down


def test_no_auto_reenable_after_hand_lost():
    m, c = on(); c.hand_lost(); c.move(5, 5); c.press()
    assert m.calls == [] and not c.enabled


def test_toggle_off_releases_button():
    m, c = on(); c.press(); c.toggle()
    assert m.calls[-1] == ("button", False) and not c.enabled


def test_cleanup_order():
    log = []
    m, c = on(); c.press()
    cleanup(c, lambda: log.append(("camera", list(m.calls), c.enabled)))
    assert log == [("camera", [("button", True), ("button", False)], False)]


def test_cleanup_releases_camera_even_if_mouse_fails():
    class Broken(LogMouse):
        def button(self, down): raise RuntimeError("boom")
    released = []
    c = Controller(Broken()); c.enabled = True; c.button_down = True
    try:
        cleanup(c, lambda: released.append(True))
    except RuntimeError:
        pass
    assert released == [True] and not c.enabled


def test_release_without_press_sends_nothing():
    m, c = on(); c.release()
    assert m.calls == []


def test_double_press_sends_one_down():
    m, c = on(); c.press(); c.press()
    assert m.calls == [("button", True)]


def test_moves_and_scrolls_when_enabled():
    m, c = on(); c.move(3, 4); c.scroll(-2)
    assert m.calls == [("move", 3, 4), ("scroll", -2)]
