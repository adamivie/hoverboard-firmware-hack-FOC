#!/usr/bin/env python3
"""Bench torque test over SWD (no serial adapter needed).
Works ONLY with hover-eferu-usart3-trq-bench-left-only.bin (sha256 7c210c5e...)."""
import socket, sys, time

CMD_R      = 0x200005A0
TOUT_CNT_R = 0x20000060
TOUT_FLG_R = 0x200005A8
RTY_LEFT   = 0x200007C8
BATV       = 0x200000B0
ENABLE     = 0x200008F9
BAT_V_SCALE = 3970 / 1492 / 100.0
TORQUE_LIMIT = 300

class OpenOCD:
    def __init__(self, host="127.0.0.1", port=6666):
        self.s = socket.create_connection((host, port), timeout=2)
    def cmd(self, c):
        self.s.sendall(c.encode() + b"\x1a")
        buf = b""
        while not buf.endswith(b"\x1a"):
            chunk = self.s.recv(4096)
            if not chunk:
                raise ConnectionError("OpenOCD closed the connection")
            buf += chunk
        return buf[:-1].decode(errors="replace").strip()
    def w16(self, a, v): self.cmd(f"mwh 0x{a:08x} 0x{v & 0xFFFF:04x}")
    def w8(self, a, v):  self.cmd(f"mwb 0x{a:08x} 0x{v & 0xFF:02x}")
    def r16(self, a):
        out = self.cmd(f"mdh 0x{a:08x} 1")
        v = int(out.split(":")[1].split()[0], 16)
        return v - 0x10000 if v & 0x8000 else v
    def r8(self, a):
        out = self.cmd(f"mdb 0x{a:08x} 1")
        return int(out.split(":")[1].split()[0], 16)

def set_cmd(o, speed):
    o.w16(CMD_R + 2, 0)
    o.w16(CMD_R + 4, speed)
    o.w16(TOUT_CNT_R, 0)
    o.w8(TOUT_FLG_R, 0)

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    target = max(-TORQUE_LIMIT, min(TORQUE_LIMIT, target))
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    o = OpenOCD()
    print("Arming with zero torque for 2 s...")
    t_end = time.time() + 2
    while time.time() < t_end:
        set_cmd(o, 0); time.sleep(0.05)
    print(f"enable={o.r8(ENABLE)}  bat={o.r16(BATV)*BAT_V_SCALE:.1f} V  err={o.r8(RTY_LEFT+6)}")
    print(f"Applying torque {target} for {duration:.0f} s")
    last = 0
    t_stop = time.time() + duration
    try:
        while time.time() < t_stop:
            set_cmd(o, target)
            if time.time() - last > 0.5:
                last = time.time()
                print(f"enable={o.r8(ENABLE)} err={o.r8(RTY_LEFT+6)} rpm={o.r16(RTY_LEFT+8)} iq={o.r16(RTY_LEFT+12)} bat={o.r16(BATV)*BAT_V_SCALE:.1f} V")
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(5):
            set_cmd(o, 0); time.sleep(0.05)
        print("Torque set to 0.")

if __name__ == "__main__":
    main()
