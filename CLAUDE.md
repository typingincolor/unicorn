# CLAUDE.md - Project Instructions

## Project Overview

This project integrates a Pimoroni Stellar Unicorn 16x16 LED matrix with Home Assistant via MQTT. The code runs on the Pico 2 W using MicroPython.

## Architecture

- **Target Hardware**: Pimoroni Stellar Unicorn (Pico 2 W, 16x16 RGB LED matrix)
- **Runtime**: MicroPython with Pimoroni firmware
- **Communication**: MQTT to Mosquitto broker on Raspberry Pi
- **Integration**: Home Assistant MQTT Discovery

## Key Files

- `config.py` - WiFi/MQTT configuration (user must edit)
- `main.py` - Main application loop, MQTT client, display control
- `effects.py` - Visual effects module (fire, rainbow, plasma, etc.)
- `home_assistant_config.yaml` - HA configuration examples

## Code Conventions

- MicroPython compatible (no asyncio beyond basic, limited stdlib)
- Use `umqtt.simple` for MQTT (not paho-mqtt)
- Hardware imports: `stellar.StellarUnicorn`, `picographics.PicoGraphics`
- Keep memory usage low - Pico has limited RAM
- Effects should be non-blocking (no long sleeps)

## MQTT Topics

All topics prefixed with `unicorn/`:
- `text/set` - Display scrolling text
- `color/set` - RGB as "R,G,B" string
- `brightness/set` - 0-255 integer
- `effect/set` - Effect name string
- `power/set` - "ON" or "OFF"
- `state` - JSON state published by device
- `availability` - "online" or "offline"

## Adding New Effects

1. Add effect method to `Effects` class in `effects.py`
2. Add effect name to `self.available` list
3. Add case to `run()` method
4. Update effect_list in HA discovery config in `main.py`

## Testing

Test MQTT from command line:
```bash
mosquitto_pub -t "unicorn/text/set" -m "Test"
mosquitto_sub -t "unicorn/#" -v
```

## Dependencies

- Pimoroni MicroPython firmware for Stellar Unicorn
- `umqtt.simple` library (install via `mip.install("umqtt.simple")`)
