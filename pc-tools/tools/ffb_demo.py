#!/usr/bin/env python3
"""Basic force-feedback demo for the hoverboard wheel (no encoder yet).

Chain: PC -> ESP32-S3 bridge (COM port) -> board USART2 -> left motor (torque mode).
Position is estimated by integrating the hall-sensor speed from the board's feedback,
so it drifts and misses very slow turns. Press C to re-centre.

Keys:  1 damper   2 spring (centring)   3 friction   4 rumble   5 kerb bumps
       0 off      C re-centre           +/- strength  Q quit
Usage: python ffb_demo.py [port=COM7]
"""
import math, msvcrt, struct, sys, time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM7"
LIMIT = 150            # hard torque cap for hands-on use (100 ~= 0.5 A)
START = 0xABCD
FB_FMT = "<HhhhhhhHH"; FB_LEN = struct.calcsize(FB_FMT)

MODES = {"0": "off", "1": "damper", "2": "spring", "3": "friction", "4": "rumble", "5": "kerb"}

def frame(speed):
    speed = int(max(-LIMIT, min(LIMIT, speed)))
    return struct.pack("<HhhH", START, 0, speed, (START ^ (speed & 0xFFFF)) & 0xFFFF)

def main():
    ser = serial.Serial(PORT, 115200, timeout=0)
    buf = bytearray(); fb = None; ok = 0
    mode = "off"; gain = 1.0
    angle = 0.0          # degrees, integrated from rpm
    rpm_f = 0.0; spring_lp = 0.0; tq_prev = 0.0
    t_prev = time.time(); t0 = t_prev
    last_print = 0
    print(__doc__)
    try:
        while True:
            now = time.time(); dt = now - t_prev; t_prev = now

            # keys
            while msvcrt.kbhit():
                k = msvcrt.getwch().lower()
                if k == "q": raise KeyboardInterrupt
                if k in MODES: mode = MODES[k]
                elif k == "c": angle = 0.0
                elif k in "+=": gain = min(2.0, gain + 0.1)
                elif k == "-": gain = max(0.1, gain - 0.1)

            # feedback
            buf += ser.read(ser.in_waiting or 0)
            while True:
                i = buf.find(b"\xcd\xab")
                if i < 0 or len(buf) - i < FB_LEN:
                    if i > 0: del buf[:i]
                    break
                f = struct.unpack(FB_FMT, buf[i:i + FB_LEN])
                x = 0
                for v in f[:-1]: x ^= v & 0xFFFF
                if x == f[-1]:
                    fb = f; ok += 1; del buf[:i + FB_LEN]
                else:
                    del buf[:i + 2]

            rpm = fb[4] if fb else 0
            angle += rpm * 6.0 * dt            # rpm * 360 / 60
            rpm_f += 0.3 * (rpm - rpm_f)

            # effects (torque sign: + spins rpm positive)
            if mode == "damper":
                tq = -0.6 * rpm
            elif mode == "spring":
                a = 0.0 if abs(angle) < 4 else angle - math.copysign(4, angle)
                raw = max(-LIMIT, min(LIMIT, -0.45 * a - 0.45 * rpm_f))
                spring_lp += 0.85 * (raw - spring_lp)
                tq = spring_lp
            elif mode == "friction":
                tq = -60 * math.tanh(rpm / 15.0)
            elif mode == "rumble":
                tq = 70 if int(now * 24) % 2 else -70
            elif mode == "kerb":
                tq = (90 if int(now * 16) % 2 else -90) if (now % 1.2) < 0.35 else 0
            else:
                tq = 0
            tq = max(-LIMIT, min(LIMIT, tq * gain))
            if mode not in ("rumble", "kerb"):   # slew limit: 8 units per 20 ms
                tq = max(tq_prev - 8, min(tq_prev + 8, tq))
            tq_prev = tq
            ser.write(frame(tq))

            if now - last_print > 0.2:
                last_print = now
                bat = f"{fb[5]/100:.1f}V" if fb else "--"
                temp = f"{fb[6]/10:.0f}C" if fb else "--"
                link = "OK" if fb else "NO FEEDBACK"
                print(f"\r[{mode:8s} x{gain:.1f}] torque={int(max(-LIMIT,min(LIMIT,tq))):+4d} "
                      f"rpm={rpm:+4d} angle~{angle:+6.0f}deg bat={bat} board={temp} link={link}   ",
                      end="", flush=True)
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(25):
            ser.write(frame(0)); time.sleep(0.02)
        ser.close()
        print("\nTorque set to 0. Bye.")

if __name__ == "__main__":
    main()
