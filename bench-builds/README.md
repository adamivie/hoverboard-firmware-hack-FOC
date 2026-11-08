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
