import serial
import time

SERIAL_PORT = '/dev/ttyACM0'  # Update if your Arduino appears on a different device
BAUD_RATE = 9600
TARGET_ID = '922422290'


def parse_serial_line(line: str):
    if line.startswith('UID:'):
        return line.replace('UID:', '').strip()
    return None


def main():
    print('Opening serial port', SERIAL_PORT)
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        print('Arduino RFID bridge connected')

        while True:
            raw = ser.readline().decode('utf-8', errors='ignore').strip()
            if not raw:
                continue

            uid = parse_serial_line(raw)
            if uid:
                print(f'RFID UID read: {uid}')
                if uid == TARGET_ID:
                    print('✅ Access Granted')
                else:
                    print('❌ Access Denied')

            elif raw == 'ACCESS_GRANTED':
                print('Arduino reports access granted')
            elif raw == 'ACCESS_DENIED':
                print('Arduino reports access denied')
            else:
                print('Arduino:', raw)


if __name__ == '__main__':
    main()
