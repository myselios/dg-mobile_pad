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


def map_to_screen(x, y, width, height, margin=0.2):
    """Map the central [margin, 1-margin] camera box to the full screen, clamped."""
    def axis(v, size):
        t = min(max((v - margin) / (1 - 2 * margin), 0.0), 1.0)
        return round(t * (size - 1))
    return axis(x, width), axis(y, height)


class OneEuroFilter:
    """One Euro filter (Casiez et al., CHI 2012): smooth when still, responsive when moving fast."""

    def __init__(self, min_cutoff=1.0, beta=0.01, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self):
        self._x = self._dx = self._t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self._t is None or t <= self._t:
            self._x, self._dx, self._t = x, 0.0, t
            return x
        dt = t - self._t
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * (x - self._x) / dt + (1 - a_d) * self._dx
        a = self._alpha(self.min_cutoff + self.beta * abs(self._dx), dt)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x


class PinchDetector:
    """Pinch with hysteresis (press < `press`, release > `release`) and a cooldown after each release."""

    def __init__(self, press=0.25, release=0.40, cooldown_s=0.3):
        self.press, self.release, self.cooldown_s = press, release, cooldown_s
        self.pressed = False
        self._last_up = float("-inf")

    def reset(self):
        self.pressed = False

    def update(self, ratio, now):
        if self.pressed and ratio > self.release:
            self.pressed = False
            self._last_up = now
            return "up"
        if not self.pressed and ratio < self.press and now - self._last_up >= self.cooldown_s:
            self.pressed = True
            return "down"
        return None
