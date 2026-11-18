from gesture_mouse.gestures import HoldTimer, finger_extended, is_open_palm, is_scroll_pose, pinch_ratio
from tests.fixtures import fist, open_palm, pinch, point_index, scale, scroll_pose


def test_open_palm():
    assert is_open_palm(open_palm()) and not is_open_palm(fist())


def test_scroll_pose():
    assert is_scroll_pose(scroll_pose()) and not is_scroll_pose(open_palm())
    assert not is_scroll_pose(point_index())


def test_index_only():
    lm = point_index()
    assert finger_extended(lm, "index") and not finger_extended(lm, "middle")
    assert not finger_extended(lm, "thumb")


def test_pinch_ratio_value_and_scale_invariant():
    assert abs(pinch_ratio(pinch(0.2)) - 0.2) < 1e-9
    assert abs(pinch_ratio(pinch(0.2)) - pinch_ratio(scale(pinch(0.2), 0.5))) < 1e-9


def test_hold_fires_once():
    h = HoldTimer(2.0)
    assert [h.update(True, t) for t in (0, 1.9, 2.0, 3, 10)] == [False, False, True, False, False]
    h.update(False, 11)
    assert h.update(True, 12) is False and h.update(True, 14) is True


def test_hold_interrupted_restarts():
    h = HoldTimer(2.0)
    h.update(True, 0); h.update(False, 1.5)
    assert h.update(True, 1.6) is False and h.update(True, 3.0) is False and h.update(True, 3.6) is True


from gesture_mouse.gestures import OneEuroFilter, map_to_screen  # noqa: E402


def test_map_center():
    assert map_to_screen(0.5, 0.5, 1000, 800) == (500, 400)


def test_map_clamps_to_screen():
    assert map_to_screen(0.0, 1.0, 1000, 800) == (0, 799)
    assert map_to_screen(0.2, 0.8, 1000, 800) == (0, 799)
    assert map_to_screen(0.95, 0.05, 1000, 800) == (999, 0)


def test_one_euro_constant():
    f = OneEuroFilter()
    assert all(abs(f(0.3, i / 30) - 0.3) < 1e-9 for i in range(30))


def test_one_euro_reduces_jitter():
    f = OneEuroFilter()
    raw = [0.5 + (0.01 if i % 2 else -0.01) for i in range(60)]
    out = [f(x, i / 30) for i, x in enumerate(raw)][10:]
    var = lambda xs: sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / len(xs)
    assert var(out) < var(raw[10:]) / 4


def test_one_euro_follows_large_move():
    f = OneEuroFilter()
    for i in range(10):
        f(0.2, i / 30)
    out = [f(0.8, (10 + i) / 30) for i in range(15)]
    assert out[-1] > 0.75


def test_one_euro_reset():
    f = OneEuroFilter(); f(0.1, 0); f.reset()
    assert f(0.9, 1) == 0.9


from gesture_mouse.gestures import PinchDetector  # noqa: E402


def test_pinch_hysteresis():
    p = PinchDetector()
    seq = [(0.5, 0), (0.2, 0.1), (0.3, 0.2), (0.35, 0.3), (0.45, 0.4)]
    assert [p.update(r, t) for r, t in seq] == [None, "down", None, None, "up"]


def test_pinch_cooldown():
    p = PinchDetector(); p.update(0.2, 0); p.update(0.5, 0.1)
    assert p.update(0.2, 0.2) is None and p.update(0.5, 0.25) is None and p.update(0.2, 0.5) == "down"


def test_pinch_no_flicker_in_band():
    p = PinchDetector(); p.update(0.2, 0)
    assert [p.update(r, 0.1 * i) for i, r in enumerate([0.26, 0.39, 0.27, 0.38], 1)] == [None] * 4 and p.pressed


def test_pinch_reset_clears_pressed():
    p = PinchDetector(); p.update(0.2, 0); p.reset()
    assert not p.pressed and p.update(0.5, 0.1) is None
