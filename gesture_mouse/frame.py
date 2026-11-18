"""Per-frame gesture -> mouse/app-action logic (stdlib only, testable in Docker).

Poses: fist 2s = control on/off; index = cursor; pinch = click/drag; index+middle = scroll;
still open palm 1s = open YouTube; palm swipe left/right = next/previous video; phone sign = voice search.
Mouse events and actions only happen while control is ON.
"""
from gesture_mouse.gestures import (HoldTimer, OneEuroFilter, PinchDetector, SwipeDetector, finger_extended,
                                    is_call_pose, is_fist, is_open_palm, is_scroll_pose, map_to_screen,
                                    pinch_ratio, scroll_delta)

FREEZE_RATIO = 0.35  # between press (0.25) and release (0.40): hold the cursor while a click is forming
STILL_DX = 0.01      # palm counts as still if the wrist moved less than this since the last frame


class FrameLogic:
    def __init__(self, controller, screen, actions):
        self.c = controller
        self.screen = screen
        self.actions = actions
        self.fist_hold = HoldTimer(2.0)
        self.palm_hold = HoldTimer(1.0)
        self.call_hold = HoldTimer(0.5)
        self.swipe = SwipeDetector()
        self.fx, self.fy = OneEuroFilter(), OneEuroFilter()
        self.pinch = PinchDetector()
        self.scroll_y = None
        self.palm_x = None
        self.palm_swiped = False
        self.ratio = 0.0
        self.pose = "-"  # shown on the overlay for debugging

    def toggle(self, now):
        self.c.toggle()
        self.pinch.reset()

    def _act(self, name):
        if self.c.enabled:
            getattr(self.actions, name)()
            return name
        return None

    def _end_palm(self, now):
        self.swipe.reset()
        self.palm_hold.update(False, now)
        self.palm_x = None
        self.palm_swiped = False

    def step(self, lm, now):
        """Process one frame's landmarks (None = no hand). Returns a status note or None."""
        if lm is None:
            self.pose = "no hand"
            self.fx.reset(); self.fy.reset(); self.pinch.reset()
            self.scroll_y = None
            self.fist_hold.update(False, now); self.call_hold.update(False, now)
            self._end_palm(now)
            if self.c.enabled:
                self.c.hand_lost()
                return "OFF: hand lost"
            return None

        dragging = self.pinch.pressed  # while dragging, other-looking poses are noise: keep dragging
        note = None
        if self.fist_hold.update(is_fist(lm) and not dragging, now):
            self.toggle(now)
            note = "toggled by fist"
        if self.call_hold.update(is_call_pose(lm) and not dragging, now):
            note = self._act("voice_search") or note

        if is_open_palm(lm) and not dragging:
            self.pose = "palm"
            self.fx.reset(); self.fy.reset(); self.pinch.reset(); self.scroll_y = None
            x = lm[0][0]
            direction = self.swipe.update(x, now)
            if direction:
                self.palm_swiped = True  # this palm was for swiping: don't also open YouTube
                note = self._act("next_video" if direction == "left" else "prev_video") or note
            still = self.palm_x is not None and abs(x - self.palm_x) < STILL_DX
            self.palm_x = x
            if self.palm_hold.update(still and not self.palm_swiped, now):
                note = self._act("open_youtube") or note
            return note
        self._end_palm(now)

        if is_scroll_pose(lm) and not dragging:
            self.pose = "scroll"
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

        if not (dragging or finger_extended(lm, "index")):
            self.pose = "fist" if is_fist(lm) else "call" if is_call_pose(lm) else "other"
            return note  # fist, phone sign, etc.: no cursor

        self.ratio = pinch_ratio(lm)
        self.pose = "drag" if dragging else "point" if self.ratio >= FREEZE_RATIO else "pinching"
        x, y = self.fx(lm[8][0], now), self.fy(lm[8][1], now)
        if self.pinch.pressed or self.ratio >= FREEZE_RATIO:
            self.c.move(*map_to_screen(x, y, *self.screen))
        event = self.pinch.update(self.ratio, now)
        if event == "down":
            self.c.press()
        elif event == "up":
            self.c.release()
        return note
