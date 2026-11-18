"""Safety gate: every mouse event goes through Controller, which starts OFF."""
from typing import Protocol


class Mouse(Protocol):
    def move(self, x: int, y: int) -> None: ...
    def button(self, down: bool) -> None: ...
    def scroll(self, dy: int) -> None: ...
    def right_click(self) -> None: ...


class LogMouse:
    """Records calls instead of posting events (dry-run and tests)."""

    def __init__(self):
        self.calls = []

    def move(self, x, y): self.calls.append(("move", x, y))
    def button(self, down): self.calls.append(("button", down))
    def scroll(self, dy): self.calls.append(("scroll", dy))
    def right_click(self): self.calls.append(("right",))


class LogActions:
    """Records app actions instead of running them (dry-run and tests)."""

    def __init__(self):
        self.calls = []

    def open_youtube(self): self.calls.append("open_youtube")
    def next_video(self): self.calls.append("next_video")
    def prev_video(self): self.calls.append("prev_video")
    def voice_search(self): self.calls.append("voice_search")


class Controller:
    def __init__(self, mouse: Mouse):
        self.mouse = mouse
        self.enabled = False
        self.button_down = False

    def toggle(self):
        if self.enabled:
            self._off()
        else:
            self.enabled = True

    def move(self, x, y):
        if self.enabled:
            self.mouse.move(x, y)

    def press(self):
        if self.enabled and not self.button_down:
            self.button_down = True  # mark first: an interrupt right after the event must still release
            self.mouse.button(True)

    def release(self):
        # Not gated on enabled: releasing must always be possible.
        if self.button_down:
            self.mouse.button(False)
            self.button_down = False  # cleared only after success, so a failed release is retried

    def scroll(self, dy):
        if self.enabled and dy:
            self.mouse.scroll(dy)

    def right_click(self):
        if self.enabled:
            self.mouse.right_click()

    def hand_lost(self):
        self._off()

    def shutdown(self):
        """Always sends one button-up (harmless if already up), then disables."""
        try:
            self.mouse.button(False)
            self.button_down = False
        finally:
            self.enabled = False

    def _off(self):
        try:
            self.release()
        finally:
            self.enabled = False

