# Hoverboard force-feedback sim wheel

A DIY force-feedback racing wheel built from a stock hoverboard hub motor and mainboard, running
[EFeru hoverboard-firmware-hack-FOC](https://github.com/EFeru/hoverboard-firmware-hack-FOC) in torque mode,
driven from a PC through an ESP32-S3.

**Status (2026-11-08):** the bench rig works end to end. The PC sends torque commands, the motor spins
smoothly in both directions, and feedback (speed, battery, temperature) comes back. There's a basic
force-feedback demo in the browser. There's no steering encoder yet, and the wheel isn't a Windows game controller yet.

```
PC (browser / Python) --USB--> ESP32-S3 (USB<->UART bridge) --UART2, long sideboard cable--> hoverboard mainboard --> hub motor
                                                                     ^
                                                    ST-Link V2 (SWD) for flashing / debug
```

## Hardware

| Part | Notes |
|---|---|
| Mainboard | JKL-PHC02-A-V02 (2015), STM32F103RCT6, 256 KB flash, single-board hoverboard controller |
| Motor | Stock 6.5" hub motor (engraved "HUS15…"), on the board's **left** channel (firmware left) |
| Power | 36 V hoverboard supply (reads ~42.7 V). Probably a ~2 A charger; see *Known issues* |
| Programmer | Clone ST-Link V2 (V2J37S7), wired with GND / SWCLK / SWDIO only. **Never connect its 3.3 V pin.** |
| PC interface | ESP32-S3-N16R8 dev board (two USB-C ports; use the one marked **USB**, the native port) |

### ESP32-S3 to board wiring (long/left sideboard cable = USART2)

| ESP32-S3 | Board (long sideboard cable) |
|---|---|
| GPIO17 (TX) | board RX (PA3) |
| GPIO18 (RX) | board TX (PA2) |
| GND | black (GND) |
| — | **red = 15 V: leave disconnected** |

Dupont pins pushed into the sideboard plug made no contact at first. Solder or clip them, and check
continuity from the S3 pin to the board-side contact.

### J1 jumper

J1 bridges the power-button input. **Bridge it only while flashing**, so the board can't power off mid-flash.
With J1 bridged the firmware's main loop waits for the "button" to be released, so it freezes: no beeps, no
commands. **Remove J1 for all running and testing**, then power on with the button.

## Firmware

All builds are EFeru FOC, torque mode, left motor only, from the fork
[adamivie/hoverboard-firmware-hack-FOC](https://github.com/adamivie/hoverboard-firmware-hack-FOC) (branch `bench-builds`, folder `bench-builds/`).

| File | Serial port | Notes | sha256 |
|---|---|---|---|
| `hover-eferu-usart2-trq-bench-left-only-hall3.bin` | **USART2 (long cable)** | **Current.** Hall order 3 baked in | `abd5e766d6c2259671fb9b9ab89e4b00bb9dd4248e49da5170371fa536fcebe7` |
| `hover-eferu-usart2-trq-bench-left-only-hallperm.bin` | USART2 | Hall order selectable live via `hallPermL` (RAM 0x2000091A) | `7eb6968cbcc0c5bb30efd1d76fa9989315d9afdb8e086fba98e0360d9038d087` |
| `hover-eferu-usart2-trq-bench-left-only.bin` | USART2 | Original hall order; motor shudders on this rig | `1240818b419db90199ea44b3a7899ab6e1b7cb5a250ac0511436221254f8594c` |
| `hover-eferu-usart3-trq-bench-left-only.bin` | USART3 (short cable) | | `7c210c5eea23a15a817080372cf5e4229cfaed2caa3ac366542e1aab4e896400` |
| `hover-eferu-usart3-trq-bench.bin` | USART3 | Both channels. Errors out with only one motor connected | `a9eed9ed0fafc6b13b4d92cbc5f2020ee8e5e942ad99b4a63df5dd4cd0f02da6` |

Why only one channel: EFeru disables **both** motors if either channel reports a hall error. With only one
motor wired, a both-channel build never drives.

Why hall order 3: the motor's phase wires were cut and re-joined, so the phase order didn't match the halls
(the motor rocked back and forth). Swapping two hall inputs in firmware is equivalent to swapping two phase wires.
A sweep over all 6 orders (`tools/hallperm_sweep.py`) found order 3 (`{0,2,1}`) spins cleanly at about ±300 rpm.

### Flashing (OpenOCD)

[xPack OpenOCD](https://github.com/xpack-dev-tools/openocd-xpack/releases) 0.12.0-7 goes in `tools/` (not committed).
STM32CubeProgrammer won't talk to this clone ST-Link.

```bash
# probe
openocd -f interface/stlink.cfg -c "set CPUTAPID 0" -f target/stm32f1x.cfg -c "adapter speed 480" -c init -c targets -c exit
# one-time only: remove factory read protection (ERASES the stock firmware), then power-cycle
openocd -f interface/stlink.cfg -c "set CPUTAPID 0" -f target/stm32f1x.cfg -c "adapter speed 480" -c init -c "reset halt" -c "stm32f1x unlock 0" -c exit
# flash + verify (J1 bridged)
openocd -f interface/stlink.cfg -c "set CPUTAPID 0" -f target/stm32f1x.cfg -c "adapter speed 200" -c init -c "reset halt" -c "program <file.bin> 0x08000000 verify reset exit"
```

The SWD leads are flaky. If you get `init mode failed` or `Fail reading CTRL/STAT`, check the board is on,
reseat or hold the leads, and retry.

### Serial protocol (EFeru, 115200 8N1, little-endian)

- Command, sent every 20 ms: `u16 0xABCD, i16 steer, i16 speed(=torque), u16 checksum = start^steer^speed`
- Feedback: `u16 0xABCD, i16 cmd1, cmd2, speedR, speedL, batVoltage(V×100), boardTemp(°C×10), u16 cmdLed, u16 checksum (XOR of all)`
- If no valid command arrives for about 0.8 s, the board zeroes torque and beeps 3×. That's normal when idle.
- Torque units: 100 ≈ 0.5 A. Motors only enable when the command is near 0, so always start by sending 0.

## Software

| Path | What |
|---|---|
| `firmware/s3_uart_bridge/` | ESP32-S3 sketch: USB CDC ⇄ UART1 (GPIO17 TX / GPIO18 RX) at 115200. Stops forwarding after 200 ms of PC silence. Build: `arduino-cli compile -b "esp32:esp32:esp32s3:CDCOnBoot=cdc" --upload -p <COM>` |
| `tools/ffb_web.html` | **Browser FFB demo** (Chrome/Edge, Web Serial). Effects: damper, spring, friction, rumble, kerb. Strength and torque-cap sliders, STOP button. Double-click to open, then **Connect wheel** and pick the S3's COM port. |
| `tools/ffb_demo.py` | Same effects as a terminal app (`python tools/ffb_demo.py COM7`). Keys 0–5, C to centre, Q to quit |
| `tools/s3_torque_test.py` | Step test: `python tools/s3_torque_test.py <torque> <seconds> <COM>` |
| `tools/hallperm_sweep.py` | Sweeps hall orders 0–5 on the `hallperm` build. Needs OpenOCD running as a server on TCL port 6666 |
| `tools/swd_torque_test.py` | Drives torque over SWD with no serial adapter. **Only** valid for `usart3-…-left-only.bin` (fixed RAM addresses) |

Safety in the demos: torque capped at ≤300 (default 200); the effect switches off when the tab is hidden; the S3
and the board both time out to zero torque if the PC stops sending.

## Known issues / next steps

- **Supply brown-out:** at torque 200 and about 370 rpm the MCU reset (RCC CSR showed POR/PDR). Probably the
  ~2 A charger. Use the battery, or a bigger supply, before raising torque or the firmware current limit.
- **No encoder:** angle is estimated by integrating hall speed (about 4° steps, and it drifts), so the spring effect is approximate.
  Plan: an LPD3806-600BM optical encoder (open-collector, pull up to 3.3 V), belt-driven off the hub at about 3–5:1, read
  by the S3's PCNT. Or an MT6701 on a 1:1 belted idler shaft for absolute angle.
- **No slip ring needed:** the axle (and all motor wiring) is stationary. Mount the wheel on the hub. Rim buttons go
  through a coiled cable or a small wireless (ESP32-C3) button box.
- **Next:** make the ESP32-S3 a USB HID PID force-feedback wheel so Windows and sims see it directly.
- The board reads about 50–55 °C at idle (MCU sensor). Keep an eye on it.
