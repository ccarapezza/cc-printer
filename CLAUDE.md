# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local copy of **Marlin 2.1.2** 3D-printer firmware, configured for one specific machine ("CC-Printer A1"). Since 2026-11-17 it is a **git repository** (branch `main`). Commit before any bulk or scripted change to `Marlin/Configuration.h` / `Configuration_adv.h`.

- **Secrets never go into git.** `.secrets` (Pi login, Cloudflare API token, Wi-Fi password) is ignored by `.gitignore`. So are the Pi-only secret files: `/etc/cloudflared/impresora.env` and `cc-webcam-secret.conf`. In `raspberry/moonraker/moonraker.conf`, the camera path is the placeholder `cam-SECRETO`. Scan the index (`git grep --cached`) for secret values before each commit.
- **Since 2026-11-16 the printer runs Klipper, not Marlin.** The Pi host config (Klipper, Moonraker, Fluidd, nginx, the camera, the Cloudflare tunnel) and the rebuild guide are in `raspberry/` (see `raspberry/README.md`). The Marlin rollback is `firmware-builds/2026-11-12-v3/firmware-v3.hex`.
- The hardware list below describes the original 2023 config. The current Marlin config (v3) uses TMC2208 standalone on X/Y/Z, 200.68 steps/mm, and a CH340 clone Mega on `/dev/ttyUSB0`.

Target hardware, from `Marlin/Configuration.h`:
- `MOTHERBOARD BOARD_RAMPS_14_EFB` (Arduino Mega 2560, AVR), `SERIAL_PORT 0`, `BAUDRATE 250000`
- Drivers: X/Y `LV8729`, Z/E0 `A4988`; 1 extruder, `INVERT_E0_DIR true`
- `DEFAULT_AXIS_STEPS_PER_UNIT { 1605.40, 1605.40, 800, 176.05 }`, bed 200×200, Z max 200
- `TEMP_SENSOR_0 5`, `TEMP_SENSOR_BED 1`, `PIDTEMP`, `EEPROM_SETTINGS`, `SDSUPPORT`
- `REPRAP_DISCOUNT_FULL_GRAPHIC_SMART_CONTROLLER` (U8glib-HAL)

Almost all per-machine work happens in `Marlin/Configuration.h` and `Marlin/Configuration_adv.h`. Keep `CONFIGURATION_H_VERSION` / `CONFIGURATION_ADV_H_VERSION` unchanged. `SanityCheck.h` rejects mismatched config versions.

## Building

The build uses PlatformIO. `platformio.ini` sets `default_envs = mega2560`, which matches this board.

```bash
pio run                      # build default env (mega2560) -> .pio/build/mega2560/firmware.hex
pio run -e mega2560 -t upload --upload-port /dev/ttyUSB0   # flash over USB
pio run -t clean
```

- Per-platform environments live in `ini/*.ini` (e.g. `ini/avr.ini`), which `platformio.ini` pulls in through `extra_configs`.
- `buildroot/share/PlatformIO/scripts/` contains pre/post build scripts. `common-dependencies.py` together with `features.ini` enables libraries and source files only when the matching `#define` is active in the configs. If a feature fails to link after you enable it, check the `[features]` mapping in `ini/features.ini`.
- `.vscode/c_cpp_properties.json` is auto-generated and holds stale Windows paths. Don't edit it.
- An 8-bit AVR target has tight flash and RAM limits. After you enable features, check the size report at the end of `pio run`.

## Config tooling

- `Marlin/config.ini` can apply config changes at build time. It currently has `ini_use_config = none`, which turns it off, so the `.h` files are authoritative. See `docs/ConfigEmbedding.md`.
- The helpers in `buildroot/bin/` edit the config headers in place:
  - `opt_set NAME value`, `opt_enable NAME...`, `opt_disable NAME...`, `opt_find`
  - `pins_set`, which edits pin files

## Tests (upstream CI harness) — caution

```bash
make tests-single-local TEST_TARGET=mega2560 ONLY_TEST=1   # one test from buildroot/tests/mega2560
make tests-all-local
make tests-single-local-docker TEST_TARGET=...             # via docker-compose
```

Each script in `buildroot/tests/<env>` calls `restore_configs` and `opt_set`/`opt_enable`, which **rewrite `Configuration.h`/`Configuration_adv.h` in place**. Between tests, `restore_configs` runs `git checkout` on the configs. That resets them to the last commit, and any uncommitted changes are lost. Don't run these tests with uncommitted config changes. Afterwards, run `git status` and `git checkout -- Marlin/Configuration*.h` to undo whatever the last test left.

In this version, "tests" means CI build checks: each one confirms that a feature combination compiles. There is no host-side unit-test suite, so the practical check is a successful `pio run`.

## Architecture

- **Entry point**: `Marlin/src/MarlinCore.cpp` has `setup()` and `loop()`. `idle()` services heaters, the LCD, SD, and endstops between moves.
- **Config pipeline**: `src/inc/MarlinConfig.h` includes `Configuration*.h`, then `Conditionals_*.h`, which derive secondary macros, then `SanityCheck.h`, which enforces compile-time errors for bad combinations. Code tests features with `ENABLED()`, `DISABLED()`, `ANY()`, `ALL()`, `TERN()`, and `TERN_()` from `src/core/macros.h`, not with bare `#ifdef`. Follow this style.
- **HAL**: `src/HAL/<platform>/` (this build uses `AVR`) implements timers, pins, the serial port, and EEPROM. Platform-independent code uses only the HAL API and fast-IO macros (`WRITE`, `READ`, `OUT_WRITE`).
- **Pins**: `src/pins/pins.h` uses `MOTHERBOARD` to pick a board file, here `src/pins/ramps/pins_RAMPS.h`.
- **Motion**: G-code is parsed in `src/gcode/` (`queue.cpp`, then `parser.cpp`, then the `GcodeSuite` handlers, one file per command under `gcode/<category>/`). Moves go through `src/module/motion.cpp`, then the look-ahead `planner.cpp`, then `stepper.cpp`, which is ISR-driven Bresenham (see `docs/Bresenham.md`). Heaters and thermal protection are in `src/module/temperature.cpp`. EEPROM persistence (M500/M501) is in `src/module/settings.cpp`.
- **Features**: optional subsystems live in `src/feature/` (leveling, runout, power loss, etc.). LCD/menu code lives in `src/lcd/`, where `marlinui` is the abstraction and `menu/` builds the menu tree.
- **Adding a G-code**: create a handler in `gcode/...`, declare it in `gcode/gcode.h`, and register it in the `process_parsed_command()` switch in `gcode/gcode.cpp`. Guard all three with the same feature conditional.
