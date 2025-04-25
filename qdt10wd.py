import serial
import time
from datetime import datetime
from serial.tools import list_ports

# Serial port scan settings
PORT_CANDIDATES = [
    port.device for port in list_ports.comports()
    if port.device.startswith('/dev/ttyUSB')
]
BAUDRATE = 115200
TIMEOUT = 1  # seconden
NUM_MEASUREMENTS = 5  # Aantal metingen

# Offset definitions
OFFSET_VOLTAGE = 7    # 2 bytes, u16, /100 -> Volt
OFFSET_CURRENT = 11   # 2 bytes, i16, /100 -> Ampère
OFFSET_SOC = 15       # 1 byte, raw SOC %

# Command to request full BMS values (voltage, current, SOC)
BMS_CMD = bytes.fromhex("7E3631303134364237453030323031464431440D")


def read_bms_response(ser):
    """
    Send the BMS command and read raw response bytes.
    Strip framing and decode hex if possible.
    """
    ser.write(BMS_CMD)
    time.sleep(0.1)
    raw = ser.read(512)
    if not raw:
        return None
    # Try hex decode
    try:
        resp_str = raw.decode(errors='ignore').strip('~\r\n')
        data = bytes.fromhex(resp_str)
    except Exception:
        data = raw
    return data


def parse_bms_data(data):
    """
    Parse voltage, current, and SOC from raw data bytes.
    """
    def u16(offset):
        return int.from_bytes(data[offset:offset+2], byteorder='big')

    def i16(offset):
        return int.from_bytes(data[offset:offset+2], byteorder='big', signed=True)

    voltage = u16(OFFSET_VOLTAGE) / 100.0
    current = i16(OFFSET_CURRENT) / 100.0
    soc_raw = data[OFFSET_SOC]
    return voltage, current, soc_raw


def find_and_open_port():
    """
    Scan candidate USB ports and return the first that opens successfully.
    """
    for port in PORT_CANDIDATES:
        try:
            ser = serial.Serial(port, BAUDRATE, timeout=TIMEOUT)
            # Test by sending one command
            data = read_bms_response(ser)
            if data:
                return ser
            ser.close()
        except (serial.SerialException, OSError):
            continue
    return None


def main():
    print("BMS uitlezing gestart...")
    ser = find_and_open_port()
    if not ser:
        print("Geen werkende /dev/ttyUSB-poort gevonden.")
        return

    # RTS/DTR setup
    ser.setRTS(True)
    ser.setDTR(False)

    try:
        for i in range(NUM_MEASUREMENTS):
            data = read_bms_response(ser)
            ts = datetime.now().strftime("%H:%M:%S")
            if data and len(data) > OFFSET_SOC:
                voltage, current, soc = parse_bms_data(data)
                print(f"[{ts}] Voltage: {voltage:.2f} V | Stroom: {current:.2f} A | SOC: {soc}%")
            else:
                print(f"[{ts}] Geen data of onvolledige respons ontvangen.")
            time.sleep(2)
    finally:
        ser.close()


if __name__ == '__main__':
    main()
