# hover-eferu-usart3-trq-bench.bin

First bench firmware for the JKL-PHC02-A-V02 mainboard (STM32F103RCT6 / GD32F103RCT6).

- Source: adamivie/hoverboard-firmware-hack-FOC @ a0751d5 (EFeru upstream), built with arm-none-eabi-gcc 13.2.1, `make -e VARIANT=VARIANT_USART`
- Changes from stock (see .config.diff):
  - Serial control + feedback on USART3 = RIGHT sideboard cable (5 V tolerant), 115200 baud
  - FOC torque mode (TRQ_MODE)
  - Bench limits: I_MOT_MAX 5 A, I_DC_MAX 7 A, N_MOT_MAX 200 rpm
  - BOARD_VARIANT 0 (standard 5-wire hall cables)
- Flash at 0x08000000 after unlocking (RDP = AA).
- sha256: a9eed9ed0fafc6b13b4d92cbc5f2020ee8e5e942ad99b4a63df5dd4cd0f02da6

## Single-motor variants (2026-11-08)
Same as the bench build, but only one motor channel enabled, so an empty channel's hall error can't disable the motor in use (Src/bldc.c:172 disables both motors if either reports an error).
- hover-eferu-usart3-trq-bench-left-only.bin  sha256 7c210c5eea23a15a817080372cf5e4229cfaed2caa3ac366542e1aab4e896400 (MOTOR_RIGHT_ENA commented out)
- hover-eferu-usart3-trq-bench-right-only.bin sha256 9456ce694a8167943bf548870f7ff0295420ec4656e1d29522131735457fdaee (MOTOR_LEFT_ENA commented out)
Flash: openocd ... -c "program <bin> 0x08000000 verify reset exit" (no unlock needed, J1 bridged).

## USART2 (long/left sensor cable) left-only variant (2026-11-08)
- hover-eferu-usart2-trq-bench-left-only.bin  sha256 1240818b419db90199ea44b3a7899ab6e1b7cb5a250ac0511436221254f8594c
  Same as the left-only bench build, but control + feedback on USART2 (PA2 TX / PA3 RX, long/left sensor cable, NOT 5 V tolerant) instead of USART3. Config delta vs the committed bench config.h: hover-eferu-usart2-trq-bench-left-only.config-vs-bench.diff
  Note: the SWD torque test script's addresses are only valid for the USART3 left-only build.

## USART2 left-only with live hall-order remap (2026-11-08)
- hover-eferu-usart2-trq-bench-left-only-hallperm.bin  sha256 7eb6968cbcc0c5bb30efd1d76fa9989315d9afdb8e086fba98e0360d9038d087
  Adds `volatile uint8_t hallPermL` (0..5, default 0 = stock order) at 0x2000091A. Write it over SWD
  (only while torque is 0) to try each hall order; equivalent to re-ordering the phase wires.
  Bake the winning value in with -DHALL_PERM_L_DEFAULT=n. Full diff vs bench source: hover-eferu-usart2-trq-bench-left-only-hallperm.diff
