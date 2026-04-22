"""Background reader for the Arduino bridge sketch (arduino_rfid_bridge.ino).

The Arduino emits three line types over USB serial at 9600 baud:
    RFID:<uid_hex>
    JOY:<x>,<y>,<button>
    SYSTEM:<message>

This module exposes a small thread-safe API so the rest of the application
can poll for RFID tags and joystick decisions without dealing with serial
parsing.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

try:
    import serial
except ImportError:  # pragma: no cover - serial only required on real hardware
    serial = None


class ArduinoBridge:
    def __init__(self, port: str, baud_rate: int = 9600,
                 deadzone_low: int = 350, deadzone_high: int = 670):
        if serial is None:
            raise RuntimeError(
                "pyserial is not installed. Run 'pip install pyserial' to use the Arduino bridge."
            )
        self.port = port
        self.baud_rate = baud_rate
        self.deadzone_low = deadzone_low
        self.deadzone_high = deadzone_high

        self._serial: Optional["serial.Serial"] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._uid_queue: deque[str] = deque(maxlen=8)
        self._decision_queue: deque[str] = deque(maxlen=8)
        self._joy_state = {"x": 512, "y": 512, "button": 1}
        self._last_button_was_down = False
        self._last_y_zone = "center"

    # ------------------------------------------------------------------ lifecycle
    def start(self):
        self._serial = serial.Serial(self.port, self.baud_rate, timeout=0.5)
        time.sleep(2)  # let Arduino reset after opening port
        try:
            self._serial.reset_input_buffer()
        except Exception:
            pass
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, name="ArduinoBridge", daemon=True)
        self._thread.start()
        print(f"Arduino bridge connected on {self.port}")

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._serial is not None and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    # ------------------------------------------------------------------ reader
    def _read_loop(self):
        assert self._serial is not None
        while not self._stop.is_set():
            try:
                raw = self._serial.readline().decode("utf-8", errors="ignore").strip()
            except Exception as exc:
                print(f"[ArduinoBridge] serial read failed: {exc}")
                time.sleep(0.2)
                continue
            if not raw:
                continue
            self._handle_line(raw)

    def _handle_line(self, line: str):
        if line.startswith("RFID:"):
            uid = line.split(":", 1)[1].strip()
            if uid:
                with self._lock:
                    self._uid_queue.append(uid)
                print(f"[ArduinoBridge] RFID received: {uid}")
        elif line.startswith("JOY:"):
            payload = line.split(":", 1)[1].strip()
            parts = payload.split(",")
            if len(parts) == 3:
                try:
                    x, y, button = (int(p) for p in parts)
                except ValueError:
                    return
                with self._lock:
                    previous_button = self._joy_state["button"]
                    self._joy_state = {"x": x, "y": y, "button": button}
                    zone = "center"
                    if y < self.deadzone_low:
                        zone = "up"
                    elif y > self.deadzone_high:
                        zone = "down"

                    if zone == "up" and self._last_y_zone != "up":
                        self._decision_queue.append("confirm")
                        print("[ArduinoBridge] Joystick decision: confirm")
                    elif zone == "down" and self._last_y_zone != "down":
                        self._decision_queue.append("retry")
                        print("[ArduinoBridge] Joystick decision: retry")

                    if button == 0 and previous_button != 0:
                        self._decision_queue.append("confirm")
                        print("[ArduinoBridge] Joystick button press: confirm")

                    self._last_y_zone = zone
        elif line.startswith("SYSTEM:"):
            print(f"[ArduinoBridge] {line.split(':', 1)[1].strip()}")
        else:
            print(f"[ArduinoBridge] raw: {line}")

    # ------------------------------------------------------------------ API
    def pop_uid(self) -> Optional[str]:
        with self._lock:
            if self._uid_queue:
                return self._uid_queue.popleft()
        return None

    def wait_for_uid(self, timeout: Optional[float] = None) -> Optional[str]:
        deadline = None if timeout is None else time.time() + timeout
        while not self._stop.is_set():
            uid = self.pop_uid()
            if uid is not None:
                return uid
            if deadline is not None and time.time() >= deadline:
                return None
            time.sleep(0.05)
        return None

    def pop_decision(self) -> Optional[str]:
        with self._lock:
            if self._decision_queue:
                return self._decision_queue.popleft()
        return None

    def joystick_state(self) -> dict:
        with self._lock:
            return dict(self._joy_state)

    def wait_for_decision(self, timeout: float = 30.0) -> Optional[str]:
        """Block until the user pushes the joystick.

        Mapping:
            push UP    -> "confirm"
            push DOWN  -> "retry"
            press BTN  -> "confirm"
        """
        # Drain stale button state so a held-down button from a previous
        # decision doesn't immediately fire.
        with self._lock:
            self._last_button_was_down = self._joy_state["button"] == 0

        start = time.time()
        while not self._stop.is_set():
            with self._lock:
                state = dict(self._joy_state)
                last_btn_down = self._last_button_was_down
                self._last_button_was_down = state["button"] == 0

            if state["y"] < self.deadzone_low:
                return "confirm"
            if state["y"] > self.deadzone_high:
                return "retry"
            if state["button"] == 0 and not last_btn_down:
                return "confirm"

            if 0 < timeout <= time.time() - start:
                return None
            time.sleep(0.05)
        return None
