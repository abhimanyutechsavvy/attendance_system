import argparse
import os
import sys
import time

import serial

try:
    import keyboard
except ImportError:
    keyboard = None


def _warn_if_not_privileged():
    """The 'keyboard' package can only inject keystrokes when running as
    Administrator on Windows or root on Linux. Without that, the script
    appears to do nothing - which is the most common cause of "joystick
    not working" reports."""
    try:
        if os.name == "nt":
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            is_admin = (os.geteuid() == 0)
    except Exception:
        is_admin = True  # don't block on detection failure

    if not is_admin:
        print(
            "[WARN] joystick.py needs Administrator (Windows) or root (Linux) "
            "privileges to inject keystrokes via the 'keyboard' library. "
            "Re-run this script from an elevated shell, otherwise no keys "
            "will reach other applications.",
            file=sys.stderr,
        )


LEFT_KEY = "left"
RIGHT_KEY = "right"
UP_KEY = "up"
DOWN_KEY = "down"
ACTION_KEY = "space"


class JoystickKeyboardBridge:
    def __init__(
        self,
        serial_port: str,
        baud_rate: int = 9600,
        deadzone_low: int = 450,
        deadzone_high: int = 570,
        poll_timeout: float = 1.0,
    ):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.deadzone_low = deadzone_low
        self.deadzone_high = deadzone_high
        self.poll_timeout = poll_timeout
        self.serial_connection = None
        self.active_keys = set()
        self.button_is_down = False

    def connect(self):
        self.serial_connection = serial.Serial(self.serial_port, self.baud_rate, timeout=self.poll_timeout)
        time.sleep(2)
        print(f"Connected to joystick on {self.serial_port} at {self.baud_rate} baud")

    def close(self):
        if keyboard is not None:
            for key in list(self.active_keys):
                keyboard.release(key)
        self.active_keys.clear()
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def update_key(self, key: str, should_press: bool):
        if should_press and key not in self.active_keys:
            keyboard.press(key)
            self.active_keys.add(key)
        elif not should_press and key in self.active_keys:
            keyboard.release(key)
            self.active_keys.remove(key)

    def parse_line(self, line: str):
        if line.startswith("JOY:"):
            line = line.split(":", 1)[1]
        elif ":" in line:
            raise ValueError(f"Ignoring non-joystick line: {line!r}")

        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            raise ValueError(f"Expected 3 comma-separated values, received: {line!r}")

        x, y, button = map(int, parts)
        return x, y, button

    def handle_input(self, x: int, y: int, button: int):
        self.update_key(LEFT_KEY, x < self.deadzone_low)
        self.update_key(RIGHT_KEY, x > self.deadzone_high)
        self.update_key(UP_KEY, y < self.deadzone_low)
        self.update_key(DOWN_KEY, y > self.deadzone_high)

        if button == 0 and not self.button_is_down:
            keyboard.press_and_release(ACTION_KEY)
            self.button_is_down = True
        elif button != 0:
            self.button_is_down = False

    def run(self):
        if keyboard is None:
            raise RuntimeError(
                "The 'keyboard' package is not installed. Install it with 'pip install keyboard' before running this script."
            )

        _warn_if_not_privileged()
        self.connect()
        print("READY - move the joystick and press Ctrl+C to stop")

        try:
            while True:
                raw_line = self.serial_connection.readline().decode("utf-8", errors="ignore").strip()
                if not raw_line:
                    continue

                try:
                    x, y, button = self.parse_line(raw_line)
                    self.handle_input(x, y, button)
                except ValueError as exc:
                    if "Ignoring non-joystick line" not in str(exc):
                        print(f"Skipping malformed joystick data: {exc}")
        finally:
            self.close()


def build_parser():
    parser = argparse.ArgumentParser(description="Use an Arduino joystick as a keyboard bridge")
    parser.add_argument("--port", required=True, help="Serial port, for example COM10 or /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=9600, help="Serial baud rate")
    parser.add_argument("--low", type=int, default=450, help="Lower deadzone threshold")
    parser.add_argument("--high", type=int, default=570, help="Upper deadzone threshold")
    return parser


def main():
    args = build_parser().parse_args()
    bridge = JoystickKeyboardBridge(
        serial_port=args.port,
        baud_rate=args.baud,
        deadzone_low=args.low,
        deadzone_high=args.high,
    )
    bridge.run()


if __name__ == "__main__":
    main()
