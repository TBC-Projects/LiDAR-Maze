#!/usr/bin/env python3

"""
RPLidar C1 → Arduino bridge

Reads scan data from RPLidar C1 over serial, bins readings into 36 × 10°
sectors (computing average and minimum distance per sector), then forwards
each frame to an Arduino over a second serial port using a simple text protocol.

Usage:
    python lidar_grabber.py --lidar-port [LIDAR USB PORT] --arduino-port [ARDUINO USB PORT] 
    python lidar_grabber.py --lidar-port [LIDAR USB PORT] --no-arduino   # debug mode

To find 
    

Protocol sent to Arduino (once per 360° scan):
    BEGIN
    0,<avg_mm>,<min_mm>
    10,<avg_mm>,<min_mm>
    ...
    350,<avg_mm>,<min_mm>
    END

Requires: pyserial  (pip install pyserial)
"""

import argparse
import time
import sys
import serial

# ── RPLidar C1 serial constants ───────────────────────────────────────────────
LIDAR_BAUD   = 460800
ARDUINO_BAUD = 115200

CMD_SCAN  = bytes([0xA5, 0x20])
CMD_STOP  = bytes([0xA5, 0x25])
CMD_RESET = bytes([0xA5, 0x40])

# Expected 7-byte response descriptor for legacy scan (0x20)
SCAN_DESCRIPTOR = bytes([0xA5, 0x5A, 0x05, 0x00, 0x00, 0x40, 0x81])

NODE_SIZE    = 5   # bytes per scan node in legacy mode
MAX_DESYNCS  = 50  # byte-by-byte resync attempts before giving up

# ── Sector constants ──────────────────────────────────────────────────────────
NUM_SECTORS  = 36
SECTOR_WIDTH = 10  # degrees per sector


# ─────────────────────────────────────────────────────────────────────────────
# Serial helpers
# ─────────────────────────────────────────────────────────────────────────────

def open_serial(port, baud, timeout=1.0):
    """Open a serial port, raise SerialException on failure."""
    ser = serial.Serial(port, baud, timeout=timeout)
    return ser


def close_serial(*ports):
    for p in ports:
        try:
            if p and p.is_open:
                p.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# RPLidar C1 protocol — legacy scan (command 0x20)
# ─────────────────────────────────────────────────────────────────────────────

def start_scan(ser):
    """
    Reset the sensor, then send the scan command and read+validate the
    7-byte response descriptor.  Raises IOError on bad descriptor.
    """
    # Reset so we start from a clean state; C1 sends an ASCII boot banner
    # ("RP S2 LIDAR System.\r\n") that must be fully drained before sending
    # the scan command — otherwise it lands in the descriptor read.
    ser.write(CMD_RESET)
    time.sleep(2.0)
    while ser.read(256):   # drain until port is silent
        pass

    ser.write(CMD_SCAN)

    desc = ser.read(7)
    if len(desc) < 7:
        raise IOError(f"Timeout reading response descriptor (got {len(desc)} bytes)")
    if desc != SCAN_DESCRIPTOR:
        raise IOError(f"Unexpected descriptor: {desc.hex()}  (expected {SCAN_DESCRIPTOR.hex()})")

    # Give the motor ~1 s to spin up before nodes start arriving
    time.sleep(1.0)


def parse_node(data):
    """
    Decode one 5-byte legacy scan node.

    Returns (angle_deg, distance_mm, quality, is_new_scan)
    or None if the check_bit is wrong (byte stream is misaligned).

    Byte layout:
      Byte 0:  quality[7:2] | start_flag[1] | NOT_start_flag[0]
      Byte 1:  angle_q6_low[7:1] | check_bit[0]   ← must be 1
      Byte 2:  angle_q6_high[7:0]
      Byte 3:  distance_q2 low byte
      Byte 4:  distance_q2 high byte

    angle    = angle_q6   / 64.0  (degrees)
    distance = distance_q2 / 4.0  (mm)
    """
    check_bit  = data[1] & 0x01
    if check_bit != 1:
        return None                        # misaligned

    # C1 layout: bit 0 = start_flag (S), bit 1 = S_inv (complement)
    start_flag = data[0]        & 0x01
    not_start  = (data[0] >> 1) & 0x01
    quality    = (data[0] >> 2) & 0x3F

    angle_q6   = (data[2] << 7) | (data[1] >> 1)
    angle      = angle_q6 / 64.0

    dist_q2    = (data[4] << 8) | data[3]
    distance   = dist_q2 / 4.0

    is_new_scan = (start_flag == 1) and (not_start == 0)
    return angle, distance, quality, is_new_scan


def _resync(ser):
    """
    Read one byte at a time looking for a valid node alignment.
    Returns the 5-byte buffer once a candidate with check_bit==1 is found,
    or raises IOError after MAX_DESYNCS attempts.
    """
    attempts = 0
    buf = bytearray(ser.read(4))   # consume the 4 bytes that were 'off'
    while attempts < MAX_DESYNCS:
        byte = ser.read(1)
        if not byte:
            raise IOError("Timeout during resync")
        buf.append(byte[0])
        if len(buf) > NODE_SIZE:
            buf.pop(0)
        if len(buf) == NODE_SIZE and (buf[1] & 0x01) == 1:
            return bytes(buf)
        attempts += 1
    raise IOError(f"Could not resync after {MAX_DESYNCS} attempts")


def collect_scan(ser):
    """
    Generator.  Yields one completed 360° scan as a list of (angle, distance)
    tuples each time a new start_flag is received.  Zero-distance readings
    (sensor returned no echo) are filtered out before yielding.
    """
    current = []
    synced  = False

    while True:
        raw = ser.read(NODE_SIZE)
        if len(raw) < NODE_SIZE:
            # Motor may still be spinning up — retry silently until data flows
            continue

        result = parse_node(raw)
        if result is None:
            # check_bit failed — byte stream is misaligned; resync
            raw    = _resync(ser)
            result = parse_node(raw)
            if result is None:
                raise IOError("Resync produced another bad node")

        angle, distance, quality, is_new_scan = result

        if is_new_scan:
            if synced and current:
                yield current          # emit the completed scan
            current = []
            synced  = True

        if synced and distance > 0:    # filter no-return readings
            current.append((angle, distance))


# ─────────────────────────────────────────────────────────────────────────────
# Sector computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_sectors(scan):
    """
    Bin (angle, distance) pairs into 36 × 10° sectors.
    Returns a list of 36 dicts: {'angle': int, 'avg': int, 'min': int}
    Sectors with no readings get avg=0, min=0.
    """
    buckets = [[] for _ in range(NUM_SECTORS)]
    for angle, distance in scan:
        idx = int(angle / SECTOR_WIDTH) % NUM_SECTORS
        buckets[idx].append(distance)

    sectors = []
    for i, readings in enumerate(buckets):
        if readings:
            avg = int(sum(readings) / len(readings))
            mn  = int(min(readings))
        else:
            avg = 0
            mn  = 0
        sectors.append({'angle': i * SECTOR_WIDTH, 'avg': avg, 'min': mn})
    return sectors


# ─────────────────────────────────────────────────────────────────────────────
# Text protocol
# ─────────────────────────────────────────────────────────────────────────────

def format_frame(sectors):
    """
    Serialise sector list to the text protocol string.

    Format:
        BEGIN
        0,<avg>,<min>
        10,<avg>,<min>
        ...
        350,<avg>,<min>
        END
    """
    lines = ["BEGIN"]
    for s in sectors:
        lines.append(f"{s['angle']},{s['avg']},{s['min']}")
    lines.append("END")
    return "\n".join(lines) + "\n"


def send_to_arduino(ser, frame):
    """Write a frame to the Arduino serial port.  Non-fatal on error."""
    try:
        ser.write(frame.encode("ascii"))
        ser.flush()
    except serial.SerialException as exc:
        print(f"[WARN] Arduino write failed: {exc}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="RPLidar C1 → Arduino bridge",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--lidar-port",    default="/dev/ttyUSB0",
                   help="Serial port for RPLidar C1")
    p.add_argument("--arduino-port",  default="/dev/ttyACM0",
                   help="Serial port for Arduino")
    p.add_argument("--lidar-baud",    type=int, default=LIDAR_BAUD)
    p.add_argument("--arduino-baud",  type=int, default=ARDUINO_BAUD)
    p.add_argument("--no-arduino",    action="store_true",
                   help="Run without Arduino (print to stdout only)")
    p.add_argument("--verbose",       action="store_true",
                   help="Print each sector on every scan")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    while True:                            # outer reconnect loop
        lidar_ser   = None
        arduino_ser = None
        try:
            print(f"[INFO] Opening LiDAR on {args.lidar_port} @ {args.lidar_baud} baud")
            lidar_ser = open_serial(args.lidar_port, args.lidar_baud)

            if not args.no_arduino:
                print(f"[INFO] Opening Arduino on {args.arduino_port} @ {args.arduino_baud} baud")
                arduino_ser = open_serial(args.arduino_port, args.arduino_baud)

            start_scan(lidar_ser)
            print("[INFO] Scan started.  Press Ctrl-C to stop.\n")

            scan_count = 0
            for scan in collect_scan(lidar_ser):
                sectors   = compute_sectors(scan)
                frame     = format_frame(sectors)
                valid     = sum(1 for s in sectors if s["avg"] > 0)
                scan_count += 1

                print(f"[SCAN #{scan_count}] {valid}/{NUM_SECTORS} sectors have data  "
                      f"({len(scan)} raw points)")

                if args.verbose:
                    for s in sectors:
                        if s["avg"] > 0:
                            print(f"  {s['angle']:3d}°  avg={s['avg']:5d} mm  "
                                  f"min={s['min']:5d} mm")

                if arduino_ser:
                    send_to_arduino(arduino_ser, frame)

        except serial.SerialException as exc:
            print(f"[ERROR] Serial error: {exc} — reconnecting in 2 s…", file=sys.stderr)
            time.sleep(2)

        except IOError as exc:
            print(f"[ERROR] Protocol error: {exc} — reconnecting in 2 s…", file=sys.stderr)
            time.sleep(2)

        except KeyboardInterrupt:
            print("\n[INFO] Stopping…")
            if lidar_ser and lidar_ser.is_open:
                try:
                    lidar_ser.write(CMD_STOP)
                except Exception:
                    pass
            break

        finally:
            close_serial(lidar_ser, arduino_ser)


if __name__ == "__main__":
    main()
