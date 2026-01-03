# Stellar Unicorn Home Assistant Integration

Control your Pimoroni Stellar Unicorn 16x16 LED matrix from Home Assistant via MQTT.

## Features

- **Text Display**: Send scrolling text messages
- **RGB Color Control**: Set any color for text or solid fill
- **Brightness Control**: Adjust brightness from Home Assistant
- **Effects**: Rainbow, Fire, Plasma, Sparkle, Matrix, Gradient
- **MQTT Discovery**: Auto-configures in Home Assistant

## Files

- `config.py` - WiFi and MQTT configuration
- `main.py` - Main application code
- `effects.py` - Visual effects module
- `home_assistant_config.yaml` - Example HA configuration and automations

## Setup Instructions

### 1. Flash Pimoroni Firmware

Download and flash the Pimoroni MicroPython firmware for Stellar Unicorn:
https://github.com/pimoroni/unicorn/releases

1. Hold BOOTSEL button on Pico W
2. Connect USB cable
3. Drag the `.uf2` file to the RPI-RP2 drive

### 2. Configure WiFi and MQTT

Copy the example config and edit with your settings:

```bash
cp config.example.py config.py
```

Edit `config.py`:

```python
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"
MQTT_BROKER = "192.168.1.x"  # Your Pi's IP address
```

### 3. Copy Files to Pico W

Using Thonny IDE or mpremote:

```bash
# Using mpremote
mpremote cp config.py :config.py
mpremote cp main.py :main.py
mpremote cp effects.py :effects.py
```

Or with Thonny:
1. Open Thonny IDE
2. Connect to Stellar Unicorn (View > Files)
3. Upload all three `.py` files

### 4. Install umqtt Library

The `umqtt.simple` library may need to be installed:

```python
# In Thonny REPL or via mpremote
import mip
mip.install("umqtt.simple")
```

### 5. Verify Mosquitto is Running

On your Raspberry Pi:

```bash
sudo systemctl status mosquitto
```

### 6. Restart Stellar Unicorn

Unplug and replug the USB cable. The display should:
1. Show blue during WiFi connection
2. Connect to MQTT
3. Register with Home Assistant

## Home Assistant Configuration

Entities should auto-discover via MQTT. If not, add the manual configuration from `home_assistant_config.yaml`.

### Control via MQTT Topics

| Topic | Payload | Description |
|-------|---------|-------------|
| `unicorn/text/set` | `Hello!` | Display scrolling text |
| `unicorn/brightness/set` | `0-255` | Set brightness |
| `unicorn/color/set` | `255,0,0` | Set RGB color |
| `unicorn/effect/set` | `rainbow` | Start effect |
| `unicorn/power/set` | `ON`/`OFF` | Turn on/off |

### Available Effects

- `none` - Stop effects
- `rainbow` - Rainbow wave
- `fire` - Flames rising from bottom
- `plasma` - Animated sine wave patterns
- `sparkle` - Random sparkles
- `matrix` - Matrix-style falling code
- `gradient` - Animated color gradient

## Testing

Test from command line on your Pi:

```bash
# Send text
mosquitto_pub -t "unicorn/text/set" -m "Hello World!"

# Change color to red
mosquitto_pub -t "unicorn/color/set" -m "255,0,0"

# Start rainbow effect
mosquitto_pub -t "unicorn/effect/set" -m "rainbow"

# Set brightness to 50%
mosquitto_pub -t "unicorn/brightness/set" -m "128"
```

## Troubleshooting

### WiFi Connection Issues
- Check SSID and password in `config.py`
- Ensure Pico W is in range of your router
- Check serial output in Thonny for errors

### MQTT Connection Issues
- Verify Mosquitto is running: `sudo systemctl status mosquitto`
- Check broker IP address in `config.py`
- Test with mosquitto_pub/sub from another device

### Display Not Updating
- Check serial output for MQTT messages
- Verify topics match between HA and Unicorn
- Ensure `umqtt.simple` is installed

### Effects Not Working
- Check `effects.py` is uploaded
- Verify effect name matches available list
- Check for import errors in serial output
