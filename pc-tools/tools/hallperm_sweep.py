#!/usr/bin/env python3
"""Sweep hallPermL 0..5 on the hallperm bench build: for each, write the perm over
OpenOCD TCL (port 6666) at zero torque, then push +T and -T via the S3 bridge.
Usage: python hallperm_sweep.py [torque=200] [port=COM7] [perms=012345]"""
import socket, struct, sys, time, threading
import serial

HALLPERM = 0x2000091A
START = 0xABCD
FB_FMT = "<HhhhhhhHH"; FB_LEN = struct.calcsize(FB_FMT)

T = max(-300, min(300, int(sys.argv[1]) if len(sys.argv) > 1 else 200))
PORT = sys.argv[2] if len(sys.argv) > 2 else "COM7"
PERMS = [int(c) for c in (sys.argv[3] if len(sys.argv) > 3 else "012345")]

ser = serial.Serial(PORT, 115200, timeout=0.01)
cmd = 0; stop = False; last = None; lock = threading.Lock()

def stream():
    global last
    buf = bytearray()
    while not stop:
        c = cmd
        ser.write(struct.pack("<HhhH", START, 0, c, (START ^ (c & 0xFFFF)) & 0xFFFF))
        buf += ser.read(ser.in_waiting or 1)
        while True:
            i = buf.find(b"\xcd\xab")
            if i < 0 or len(buf) - i < FB_LEN:
                if i > 0: del buf[:i]
                break
            f = struct.unpack(FB_FMT, buf[i:i + FB_LEN])
            x = 0
            for v in f[:-1]: x ^= v & 0xFFFF
            if x == f[-1]:
                with lock: last = f
                del buf[:i + FB_LEN]
            else:
                del buf[:i + 2]
        time.sleep(0.02)

def tcl(c):
    s = socket.create_connection(("127.0.0.1", 6666), timeout=2)
    s.sendall(c.encode() + b"\x1a"); out = b""
    while not out.endswith(b"\x1a"): out += s.recv(4096)
    s.close(); return out[:-1].decode().strip()

def phase(torque, secs):
    global cmd
    cmd = torque; rpms = []; t_end = time.time() + secs
    while time.time() < t_end:
        time.sleep(0.1)
        with lock: f = last
        if f: rpms.append(f[4])
    return rpms

th = threading.Thread(target=stream, daemon=True); th.start()
try:
    phase(0, 1.5)
    for n in PERMS:
        cmd = 0; time.sleep(0.5)
        tcl(f"mwb 0x{HALLPERM:08x} {n}")
        rb = tcl(f"mdb 0x{HALLPERM:08x} 1")
        phase(0, 1.0)
        t0 = time.strftime("%H:%M:%S")
        fwd = phase(T, 3); mid = phase(0, 1.5); rev = phase(-T, 3); phase(0, 2)
        with lock: f = last
        def summ(r):
            if not r: return "no data"
            flips = sum(1 for a, b in zip(r, r[1:]) if a * b < 0)
            return f"min={min(r)} max={max(r)} end={r[-1]} signflips={flips}"
        print(f"perm {n} (start {t0}, readback {rb}): +{T}: {summ(fwd)} | -{T}: {summ(rev)} | bat={f[5]/100:.1f}V temp={f[6]/10:.1f}C", flush=True)
finally:
    cmd = 0; time.sleep(0.5); stop = True; th.join(1)
    for _ in range(10):
        ser.write(struct.pack("<HhhH", START, 0, 0, START)); time.sleep(0.02)
    ser.close()
    print("Torque set to 0.")
