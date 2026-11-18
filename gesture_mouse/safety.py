"""Safety gate: every mouse event goes through Controller, which starts OFF."""
from typing import Callable, Protocol


class Mouse(Protocol):
    def move(self, x: int, y: int) -> None: ...
    def button(self, down: bool) -> None: ...
    def scroll(self, dy: int) -> None: ...


class LogMouse:
    """Records calls instead of posting events (dry-run and tests)."""

    def __init__(self):
        self.calls = []

    def move(self, x, y): self.calls.append(("move", x, y))
    def button(self, down): self.calls.append(("button", down))
    def scroll(self, dy): self.calls.append(("scroll", dy))


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
            self.mouse.button(True)
            self.button_down = True

    def release(self):
        # Not gated on enabled: releasing must always be possible.
        if self.button_down:
            self.button_down = False
            self.mouse.button(False)

    def scroll(self, dy):
        if self.enabled and dy:
            self.mouse.scroll(dy)

    def hand_lost(self):
        self._off()

    def shutdown(self):
        self._off()

    def _off(self):
        try:
            self.release()
        finally:
            self.enabled = False


def cleanup(controller: Controller, release_camera: Callable[[], None]) -> None:
    """Fixed order: release button -> control off -> camera."""
    try:
        controller.shutdown()
        print("[cleanup] button released, control off", flush=True)
    finally:
        release_camera()
        print("[cleanup] camera released", flush=True)
