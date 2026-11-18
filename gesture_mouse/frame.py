"""Per-frame gesture -> mouse logic (stdlib only, testable in Docker)."""
from gesture_mouse.gestures import (HoldTimer, OneEuroFilter, PinchDetector, is_open_palm, is_scroll_pose,
                                    map_to_screen, pinch_ratio, scroll_delta)

FREEZE_RATIO = 0.35  # between press (0.25) and release (0.40): hold the cursor while a click is forming


class FrameLogic:
    def __init__(self, controller, screen):
        self.c = controller
        self.screen = screen
        self.palm = HoldTimer(2.0)
        self.fx, self.fy = OneEuroFilter(), OneEuroFilter()
        self.pinch = PinchDetector()
        self.scroll_y = None
        self.ratio = 0.0

    def toggle(self, now):
        self.c.toggle()
        self.pinch.reset()

    def step(self, lm, now):
        """Process one frame's landmarks (None = no hand). Returns a status note or None."""
        if lm is None:
            self.fx.reset(); self.fy.reset(); self.pinch.reset()
            self.scroll_y = None
            self.palm.update(False, now)
            if self.c.enabled:
                self.c.hand_lost()
                return "OFF: hand lost"
            return None

        note = None
        if self.palm.update(is_open_palm(lm), now):
            self.toggle(now)
            note = "toggled by palm"

        # While dragging, a scroll-looking frame is pose noise: keep dragging.
        if is_scroll_pose(lm) and not self.pinch.pressed:
            self.c.release()  # no-op unless something else pressed; never leave a button down
            self.fx.reset(); self.fy.reset(); self.pinch.reset()
            y = (lm[8][1] + lm[12][1]) / 2
            if self.scroll_y is None:
                self.scroll_y = y
            elif dy := scroll_delta(self.scroll_y, y):
                self.c.scroll(dy)
                self.scroll_y = y  # keep the anchor until we scroll, so slow moves still add up
            return note

        self.scroll_y = None
        self.ratio = pinch_ratio(lm)
        x, y = self.fx(lm[8][0], now), self.fy(lm[8][1], now)
        if self.pinch.pressed or self.ratio >= FREEZE_RATIO:
            self.c.move(*map_to_screen(x, y, *self.screen))
        event = self.pinch.update(self.ratio, now)
        if event == "down":
            self.c.press()
        elif event == "up":
            self.c.release()
        return note
