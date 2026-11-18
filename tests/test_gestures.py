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
