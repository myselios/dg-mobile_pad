"""Real mouse events via CoreGraphics (macOS only)."""
import Quartz as Q


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

    def _post(self, event_type, pos):
        ev = Q.CGEventCreateMouseEvent(None, event_type, pos, Q.kCGMouseButtonLeft)
        Q.CGEventPost(Q.kCGHIDEventTap, ev)

    def move(self, x, y):
        self._pos = (x, y)
        self._post(Q.kCGEventLeftMouseDragged if self._down else Q.kCGEventMouseMoved, self._pos)

    def button(self, down):
        self._down = down
        self._post(Q.kCGEventLeftMouseDown if down else Q.kCGEventLeftMouseUp, self._pos)

    def scroll(self, dy):
        Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateScrollWheelEvent(None, Q.kCGScrollEventUnitPixel, 1, int(dy)))
