"""Phone trackpad messages -> Controller (stdlib only, testable in Docker).

Messages are JSON objects from the phone page, e.g. {"t": "move", "dx": 3.5, "dy": -1}.
Everything arriving here is untrusted input: validate, never getattr on raw names.
"""
import math

ACTIONS = {"open_youtube", "next_video", "prev_video", "voice_search"}
MAX_DELTA = 500.0  # px per message; anything bigger is a bug or an attack


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and abs(v) <= MAX_DELTA


class RemoteHandler:
    def __init__(self, controller, actions, screen, get_pos, speed=1.5, accel=0.06, scroll_gain=1.0):
        self.c, self.actions, self.screen, self.get_pos = controller, actions, screen, get_pos
        self.speed, self.accel, self.scroll_gain = speed, accel, scroll_gain

    def target(self, x, y, dx, dy):
        """Relative move with pointer acceleration (faster swipes travel further), clamped to the screen."""
        gain = self.speed * (1 + self.accel * math.hypot(dx, dy))
        w, h = self.screen
        return (min(max(round(x + dx * gain), 0), w - 1), min(max(round(y + dy * gain), 0), h - 1))

    def handle(self, msg):
        t = msg.get("t") if isinstance(msg, dict) else None
        if t == "move" and _num(msg.get("dx")) and _num(msg.get("dy")):
            self.c.move(*self.target(*self.get_pos(), msg["dx"], msg["dy"]))
        elif t == "scroll" and _num(msg.get("dy")):
            self.c.scroll(round(msg["dy"] * self.scroll_gain))  # natural: finger up -> negative -> content up
        elif t == "click":
            self.c.press(); self.c.release()
        elif t == "right":
            self.c.right_click()
        elif t == "down":
            self.c.press()
        elif t == "up":
            self.c.release()
        elif t == "on":
            if not self.c.enabled:
                self.c.toggle()
        elif t == "off":
            if self.c.enabled:
                self.c.toggle()
        elif t == "action" and msg.get("name") in ACTIONS:
            if self.c.enabled:
                getattr(self.actions, msg["name"])()
        else:
            return "bad message"
        return None

    def disconnected(self):
        self.c.shutdown()
