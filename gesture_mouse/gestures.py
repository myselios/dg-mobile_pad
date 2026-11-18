"""Pure gesture logic (stdlib only, so it is testable in Docker).

Landmarks: list of 21 (x, y) normalized points in MediaPipe order.
"""
import math

TIP = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
PIP = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}


def finger_extended(lm, finger):
    if finger == "thumb":
        return math.dist(lm[4], lm[9]) > math.dist(lm[3], lm[9])
    return math.dist(lm[TIP[finger]], lm[0]) > math.dist(lm[PIP[finger]], lm[0])


def is_open_palm(lm):
    return all(finger_extended(lm, f) for f in ("thumb", "index", "middle", "ring", "pinky"))


def is_scroll_pose(lm):
    return (finger_extended(lm, "index") and finger_extended(lm, "middle")
            and not finger_extended(lm, "ring") and not finger_extended(lm, "pinky"))


def pinch_ratio(lm):
    """Thumb-index tip distance divided by hand size (wrist to middle MCP)."""
    return math.dist(lm[4], lm[8]) / max(math.dist(lm[0], lm[9]), 1e-9)


class HoldTimer:
    """Fires once when `active` has been held for hold_s; re-arms only after active goes False."""

    def __init__(self, hold_s=2.0):
        self.hold_s = hold_s
        self._since = None
        self._fired = False

    def update(self, active, now):
        if not active:
            self._since, self._fired = None, False
            return False
        if self._since is None:
            self._since = now
        if not self._fired and now - self._since >= self.hold_s:
            self._fired = True
            return True
        return False
