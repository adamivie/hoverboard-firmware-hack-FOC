#!/usr/bin/env python3
"""Bench torque test through the ESP32-S3 USB<->UART bridge (EFeru serial protocol).
Usage: python s3_torque_test.py [torque=80] [seconds=3] [port=COM6]
Wheel off the ground, hands clear. Torque capped at +/-300; always sends 0 on exit."""
import struct, sys, time
import serial

START = 0xABCD
LIMIT = 300
FB_FMT = "<HhhhhhhHH"          # start, cmd1, cmd2, speedR, speedL, bat, temp, cmdLed, checksum
FB_LEN = struct.calcsize(FB_FMT)

def frame(steer, speed):
    chk = (START ^ (steer & 0xFFFF) ^ (speed & 0xFFFF)) & 0xFFFF
    return struct.pack("<HhhH", START, steer, speed, chk)

class FbParser:
    def __init__(self):
        self.buf = bytearray(); self.ok = 0; self.bad = 0; self.last = None
    def feed(self, data):
        self.buf += data
        while True:
            i = self.buf.find(b"\xcd\xab")
            if i < 0:
                del self.buf[:-1]; return
            if len(self.buf) - i < FB_LEN:
                del self.buf[:i]; return
            f = struct.unpack(FB_FMT, self.buf[i:i + FB_LEN])
            chk = 0
            for v in f[:-1]:
                chk ^= v & 0xFFFF
            if chk == f[-1]:
                self.ok += 1; self.last = f; del self.buf[:i + FB_LEN]
            else:
                self.bad += 1; del self.buf[:i + 2]

def status(p, t):
    if p.last is None:
        return f"t={t:+4d}  no feedback yet (ok={p.ok} bad={p.bad})"
    _, c1, c2, sR, sL, bat, temp, led, _ = p.last
    return (f"t={t:+4d}  cmd1={c1} cmd2={c2} rpmL={sL} rpmR={sR} "
            f"bat={bat/100:.1f}V temp={temp/10:.1f}C ok={p.ok} bad={p.bad}")

def run(ser, p, torque, secs, label):
    print(label)
    t_end = time.time() + secs; last_print = 0
    while time.time() < t_end:
        ser.write(frame(0, torque))
        p.feed(ser.read(ser.in_waiting or 1))
        if time.time() - last_print > 0.2:
            last_print = time.time(); print("  " + status(p, torque))
        time.sleep(0.02)

def main():
    torque = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    torque = max(-LIMIT, min(LIMIT, torque))
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    port = sys.argv[3] if len(sys.argv) > 3 else "COM6"
    ser = serial.Serial(port, 115200, timeout=0.01)
    p = FbParser()
    try:
        run(ser, p, 0, 1.0, "Arming with 0 for 1 s")
        run(ser, p, torque, secs, f"Torque {torque} for {secs:.0f} s")
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(25):
            ser.write(frame(0, 0)); time.sleep(0.02)
        p.feed(ser.read(ser.in_waiting or 1))
        print("Torque set to 0.  " + status(p, 0))
        ser.close()

if __name__ == "__main__":
    main()

