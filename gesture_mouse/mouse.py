"""Real mouse events via CoreGraphics (macOS only)."""
import math
import time

import Quartz as Q

DOUBLE_CLICK_S = 0.5


def screen_size():
    """Main display size in points (the unit CGEvent uses)."""
    b = Q.CGDisplayBounds(Q.CGMainDisplayID())
    return int(b.size.width), int(b.size.height)


def can_post_events():
    """True if this process may post events (Accessibility granted). None if the API is unavailable."""
    fn = getattr(Q, "CGPreflightPostEventAccess", None)
    return bool(fn()) if fn else None


class QuartzMouse:
    def __init__(self):
        loc = Q.CGEventGetLocation(Q.CGEventCreate(None))
        self._pos = (loc.x, loc.y)
        self._down = False
        self._last_click = (0.0, (0.0, 0.0))
        self._clicks = 1

    def position(self):
        loc = Q.CGEventGetLocation(Q.CGEventCreate(None))
        return loc.x, loc.y

    def _post(self, event_type, pos, button=Q.kCGMouseButtonLeft, clicks=None):
        ev = Q.CGEventCreateMouseEvent(None, event_type, pos, button)
        if clicks:
            # Apps only see a double-click if the event says so.
            Q.CGEventSetIntegerValueField(ev, Q.kCGMouseEventClickState, clicks)
        Q.CGEventPost(Q.kCGHIDEventTap, ev)

    def move(self, x, y):
        self._pos = (x, y)
        self._post(Q.kCGEventLeftMouseDragged if self._down else Q.kCGEventMouseMoved, self._pos)

    def button(self, down):
        self._down = down
        self._pos = self.position()  # click where the cursor really is (the real trackpad may have moved it)
        if down:
            now, (t, p) = time.monotonic(), self._last_click
            self._clicks = self._clicks + 1 if now - t < DOUBLE_CLICK_S and math.dist(p, self._pos) < 5 else 1
            self._last_click = (now, self._pos)
        self._post(Q.kCGEventLeftMouseDown if down else Q.kCGEventLeftMouseUp, self._pos, clicks=self._clicks)

    def right_click(self):
        self._pos = self.position()
        for t in (Q.kCGEventRightMouseDown, Q.kCGEventRightMouseUp):
            self._post(t, self._pos, Q.kCGMouseButtonRight)

    def scroll(self, dy):
        Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateScrollWheelEvent(None, Q.kCGScrollEventUnitPixel, 1, int(dy)))
