import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO = None
    GPIO_AVAILABLE = False

try:
    from mfrc522 import SimpleMFRC522
except ImportError:
    SimpleMFRC522 = None

from config import BUTTON_CONFIRM_PIN, BUTTON_RETRY_PIN


class NFCReader:
    def __init__(self, arduino_bridge=None):
        self.arduino_bridge = arduino_bridge
        if self.arduino_bridge is not None:
            self.simulated = False
            print("NFC reader using Arduino serial bridge.")
            return

        self.simulated = SimpleMFRC522 is None
        if not self.simulated:
            try:
                self.reader = SimpleMFRC522()
            except Exception as exc:
                print(f"[WARN] NFC initialization failed: {exc}")
                self.simulated = True
        if self.simulated:
            print("[WARN] NFC hardware unavailable. Using manual tag input.")

    def wait_for_tag(self):
        if self.arduino_bridge is not None:
            print("Please tap your NFC ID card on the reader...")
            uid = self.arduino_bridge.wait_for_uid(timeout=None)
            if uid:
                print(f"NFC tag detected: {uid}")
            return uid

        if self.simulated:
            tag_id = input("[SIM] Enter NFC tag ID (or press Enter to retry): ").strip()
            return tag_id if tag_id else None

        print("Please tap your NFC ID card on the reader...")
        try:
            tag_id, _ = self.reader.read()
            tag_id_str = str(tag_id).strip()
            print(f"NFC tag detected: {tag_id_str}")
            return tag_id_str
        except Exception as exc:
            print(f"Error reading NFC tag: {exc}")
            return None


class VerificationButton:
    def __init__(self, pin: int):
        self.pin = pin
        self.simulated = not GPIO_AVAILABLE
        if self.simulated:
            print(f"[WARN] GPIO unavailable. Button on pin {pin} will be simulated.")
        else:
            try:
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception as exc:
                print(f"[WARN] GPIO setup failed for pin {pin}: {exc}")
                self.simulated = True

    def is_pressed(self):
        if self.simulated:
            return False
        return GPIO.input(self.pin) == GPIO.LOW


class ButtonController:
    def __init__(self, confirm_pin: int = BUTTON_CONFIRM_PIN, retry_pin: int = BUTTON_RETRY_PIN,
                 arduino_bridge=None):
        self.arduino_bridge = arduino_bridge
        if self.arduino_bridge is not None:
            self.simulated = False
            print("Button input using Arduino joystick (UP=confirm, DOWN=retry, click=confirm).")
            return

        self.simulated = not GPIO_AVAILABLE
        if not self.simulated:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
            except Exception as exc:
                print(f"[WARN] GPIO initialization failed: {exc}")
                self.simulated = True

        self.confirm_button = VerificationButton(confirm_pin)
        self.retry_button = VerificationButton(retry_pin)
        self.simulated = self.simulated or self.confirm_button.simulated or self.retry_button.simulated
        if self.simulated:
            print("[WARN] Button input will use manual simulation.")

    def wait_for_decision(self, timeout: int = 30):
        if self.arduino_bridge is not None:
            print("Push joystick UP to confirm or DOWN to retry (click also confirms).")
            return self.arduino_bridge.wait_for_decision(timeout=timeout)

        if self.simulated:
            # Use the OpenCV window for input so it stays responsive on Windows.
            try:
                import cv2
                print("[SIM] Press C in the window to confirm, R to retry, Q to quit.")
                start = time.time()
                while True:
                    key = cv2.waitKey(50) & 0xFF
                    if key == ord('c'):
                        return "confirm"
                    if key == ord('r'):
                        return "retry"
                    if key == ord('q') or key == 27:  # Q or ESC
                        return None
                    if 0 < timeout <= time.time() - start:
                        print("Button input timed out.")
                        return None
            except Exception:
                # Fallback to stdin if cv2 isn't available.
                print("[SIM] Type 'confirm' or 'retry' and press Enter.")
                start = time.time()
                while True:
                    if time.time() - start > timeout:
                        print("Button input timed out.")
                        return None
                    choice = input("[SIM] Decision: ").strip().lower()
                    if choice in {"confirm", "retry"}:
                        return choice
                    print("Please type 'confirm' or 'retry'.")

        print("Press green to confirm or red to retry.")
        start = time.time()
        while True:
            if self.confirm_button.is_pressed():
                time.sleep(0.2)
                return "confirm"
            if self.retry_button.is_pressed():
                time.sleep(0.2)
                return "retry"
            if 0 < timeout <= time.time() - start:
                print("Button input timed out.")
                return None
            time.sleep(0.05)

    def cleanup(self):
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception:
                pass
