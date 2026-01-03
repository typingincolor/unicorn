# Space Unicorn - Home Assistant MQTT Integration
# For Stellar Unicorn 16x16 LED Matrix

import time
import json
import network
import machine
import ntptime
from umqtt.simple import MQTTClient
from stellar import StellarUnicorn
from picographics import PicoGraphics, DISPLAY_STELLAR_UNICORN as DISPLAY

import config
from effects import Effects

# Initialize hardware
su = StellarUnicorn()
graphics = PicoGraphics(DISPLAY)
WIDTH = StellarUnicorn.WIDTH
HEIGHT = StellarUnicorn.HEIGHT

# State variables
current_text = ""
current_brightness = 0.5
current_color = (255, 255, 255)  # RGB
current_bg_color = (0, 0, 0)  # RGB
current_effect = "none"
power_on = True
text_scroll_position = 0
last_scroll_time = 0
SCROLL_SPEED = 0.075  # seconds between scroll steps

# Sensor status display
# Format: {"luke": "open", "front": "closed", "back": "closed"}
sensor_status = {}
show_sensors = True  # Default to clock/sensor mode
sensor_scroll_pos = WIDTH
last_sensor_scroll = 0

# Effects manager
effects = Effects(su, graphics, WIDTH, HEIGHT)

# WiFi connection
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"Already connected: {wlan.ifconfig()[0]}")
        return wlan

    print(f"Connecting to {config.WIFI_SSID}...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    max_wait = 20
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)

    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed")

    print(f"Connected! IP: {wlan.ifconfig()[0]}")
    return wlan


def sync_time():
    """Sync time via NTP"""
    try:
        print("Syncing time via NTP...")
        ntptime.settime()

        # Get current UTC time and apply timezone offset
        utc_time = time.time()
        tm = time.localtime(utc_time)

        # Determine timezone offset
        if config.TIMEZONE_OFFSET is not None:
            offset_hours = config.TIMEZONE_OFFSET
        else:
            # Auto-detect BST (rough: April-October = +1)
            month = tm[1]
            if 4 <= month <= 10:
                offset_hours = 1  # BST
            else:
                offset_hours = 0  # GMT

        local_time = utc_time + (offset_hours * 3600)
        tm = time.localtime(local_time)

        # Set RTC to local time
        rtc = machine.RTC()
        rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

        print(f"Time synced: {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} (UTC{'+' if offset_hours >= 0 else ''}{offset_hours})")
        return True
    except Exception as e:
        print(f"NTP sync failed: {e}")
        return False


# MQTT callbacks
def on_message(topic, msg):
    global current_text, current_brightness, current_color, current_bg_color
    global current_effect, power_on, text_scroll_position
    global sensor_status, show_sensors, sensor_scroll_pos

    topic = topic.decode()
    msg = msg.decode()

    print(f"MQTT: {topic} = {msg}")

    if topic == config.MQTT_TOPIC_TEXT:
        current_text = msg
        text_scroll_position = WIDTH  # Start from right edge
        current_effect = "none"  # Stop effects when showing text
        show_sensors = False  # Hide sensors when showing text

    elif topic == config.MQTT_TOPIC_BRIGHTNESS:
        try:
            # Brightness 0-255 from HA, convert to 0.0-1.0
            current_brightness = int(msg) / 255.0
            su.set_brightness(current_brightness)
        except ValueError:
            pass

    elif topic == config.MQTT_TOPIC_COLOR:
        try:
            # Color as "R,G,B" string
            r, g, b = [int(x) for x in msg.split(",")]
            current_color = (r, g, b)
        except (ValueError, IndexError):
            pass

    elif topic == config.MQTT_TOPIC_EFFECT:
        current_effect = msg.lower()
        if current_effect == "clock":
            # Switch back to clock/sensor mode
            show_sensors = True
            current_text = ""
            current_effect = "none"
        elif current_effect != "none":
            current_text = ""  # Clear text when showing effect
            show_sensors = False  # Hide sensors when showing effect

    elif topic == config.MQTT_TOPIC_POWER:
        power_on = msg.lower() in ("on", "true", "1")
        if not power_on:
            clear_display()

    elif topic == config.MQTT_TOPIC_SENSORS:
        try:
            # JSON format: {"luke": "open", "front": "closed", "back": "closed"}
            sensor_status = json.loads(msg)
            show_sensors = True
            current_text = ""  # Clear text
            current_effect = "none"  # Stop effects
            sensor_scroll_pos = WIDTH  # Reset scroll position
        except (ValueError, TypeError):
            pass

    publish_state()


def clear_display():
    graphics.set_pen(graphics.create_pen(0, 0, 0))
    graphics.clear()
    su.update(graphics)


def publish_state():
    """Publish current state to Home Assistant"""
    state = {
        "state": "ON" if power_on else "OFF",
        "brightness": int(current_brightness * 255),
        "color": {"r": current_color[0], "g": current_color[1], "b": current_color[2]},
        "effect": current_effect,
        "text": current_text
    }
    try:
        mqtt_client.publish(config.MQTT_TOPIC_STATE, json.dumps(state))
    except:
        pass


def publish_ha_discovery():
    """Publish Home Assistant MQTT Discovery config"""

    # Light entity with RGB and effects
    light_config = {
        "name": "Stellar Unicorn",
        "unique_id": "stellar_unicorn_light",
        "command_topic": config.MQTT_TOPIC_POWER,
        "state_topic": config.MQTT_TOPIC_STATE,
        "state_value_template": "{{ value_json.state }}",
        "brightness_command_topic": config.MQTT_TOPIC_BRIGHTNESS,
        "brightness_state_topic": config.MQTT_TOPIC_STATE,
        "brightness_value_template": "{{ value_json.brightness }}",
        "rgb_command_topic": config.MQTT_TOPIC_COLOR,
        "rgb_command_template": "{{ red }},{{ green }},{{ blue }}",
        "rgb_state_topic": config.MQTT_TOPIC_STATE,
        "rgb_value_template": "{{ value_json.color.r }},{{ value_json.color.g }},{{ value_json.color.b }}",
        "effect_command_topic": config.MQTT_TOPIC_EFFECT,
        "effect_state_topic": config.MQTT_TOPIC_STATE,
        "effect_value_template": "{{ value_json.effect }}",
        "effect_list": ["none", "rainbow", "fire", "plasma", "sparkle", "matrix", "gradient"],
        "availability_topic": config.MQTT_TOPIC_AVAILABILITY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": {
            "identifiers": ["stellar_unicorn"],
            "name": "Stellar Unicorn",
            "model": "Stellar Unicorn 16x16",
            "manufacturer": "Pimoroni"
        }
    }

    # Text input entity
    text_config = {
        "name": "Stellar Unicorn Text",
        "unique_id": "stellar_unicorn_text",
        "command_topic": config.MQTT_TOPIC_TEXT,
        "state_topic": config.MQTT_TOPIC_STATE,
        "value_template": "{{ value_json.text }}",
        "availability_topic": config.MQTT_TOPIC_AVAILABILITY,
        "device": {
            "identifiers": ["stellar_unicorn"]
        }
    }

    # Publish discovery configs
    mqtt_client.publish(
        f"{config.HA_DISCOVERY_PREFIX}/light/stellar_unicorn/config",
        json.dumps(light_config),
        retain=True
    )

    mqtt_client.publish(
        f"{config.HA_DISCOVERY_PREFIX}/text/stellar_unicorn_text/config",
        json.dumps(text_config),
        retain=True
    )

    print("Published HA Discovery config")


def draw_text():
    """Draw scrolling text on display"""
    global text_scroll_position, last_scroll_time

    if not current_text:
        return False

    # Set background
    bg_pen = graphics.create_pen(*current_bg_color)
    graphics.set_pen(bg_pen)
    graphics.clear()

    # Set text color and font
    text_pen = graphics.create_pen(*current_color)
    graphics.set_pen(text_pen)
    graphics.set_font("bitmap8")

    # Measure text width
    text_width = graphics.measure_text(current_text, 1)

    # Draw text at current scroll position
    # Center vertically (16 pixels high, ~8 pixel font)
    y_pos = (HEIGHT - 8) // 2
    graphics.text(current_text, int(text_scroll_position), y_pos, -1, 1)

    # Update scroll position
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_scroll_time) > SCROLL_SPEED * 1000:
        last_scroll_time = current_time
        text_scroll_position -= 1

        # Reset when text has scrolled off screen
        if text_scroll_position < -text_width:
            text_scroll_position = WIDTH

    return True


def draw_clock():
    """Draw current time with hours on top, minutes on bottom"""
    # Clear display
    graphics.set_pen(graphics.create_pen(0, 0, 0))
    graphics.clear()

    # Get current time from RTC
    current_time = machine.RTC().datetime()
    hours = current_time[4]
    mins = current_time[5]

    hours_str = f"{hours:02d}"
    mins_str = f"{mins:02d}"

    # Muted teal color (brighter to account for brightness reduction)
    graphics.set_pen(graphics.create_pen(0, 150, 120))
    graphics.set_font("bitmap8")

    # Hours on top row (centered, shifted 1 pixel left)
    hours_width = graphics.measure_text(hours_str, 1)
    hours_x = (WIDTH - hours_width) // 2 - 1
    graphics.text(hours_str, hours_x, 2, -1, 1)

    # Minutes on bottom row (centered, shifted 1 pixel left)
    mins_width = graphics.measure_text(mins_str, 1)
    mins_x = (WIDTH - mins_width) // 2 - 1
    graphics.text(mins_str, mins_x, 9, -1, 1)


def draw_sensors():
    """Draw open doors as scrolling red text, or clock if all secure"""
    global sensor_scroll_pos, last_sensor_scroll

    if not sensor_status:
        return False

    # Build list of OPEN doors only
    open_doors = []
    for name, status in sensor_status.items():
        is_open = status.lower() in ("open", "on", "true", "1")
        if is_open:
            open_doors.append(name.upper())

    # If all doors closed, show clock
    if not open_doors:
        draw_clock()
        return True

    # Clear display
    graphics.set_pen(graphics.create_pen(0, 0, 0))
    graphics.clear()

    # Red color for alerts
    red = graphics.create_pen(255, 0, 0)
    graphics.set_pen(red)
    graphics.set_font("bitmap8")

    # Calculate total width
    total_width = 0
    for name in open_doors:
        total_width += graphics.measure_text(name + "  ", 1)

    # Draw each open door name
    y_pos = (HEIGHT - 8) // 2
    x_pos = int(sensor_scroll_pos)

    for name in open_doors:
        graphics.text(name + "  ", x_pos, y_pos, -1, 1)
        x_pos += graphics.measure_text(name + "  ", 1)

    # Update scroll position
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_sensor_scroll) > SCROLL_SPEED * 1000:
        last_sensor_scroll = current_time
        sensor_scroll_pos -= 1

        # Reset when scrolled off screen
        if sensor_scroll_pos < -total_width:
            sensor_scroll_pos = WIDTH

    return True


def update_display():
    """Main display update function"""
    if not power_on:
        return

    if show_sensors:
        draw_sensors()
        su.update(graphics)
    elif current_effect != "none" and current_effect in effects.available:
        effects.run(current_effect)
    elif current_text:
        draw_text()
        su.update(graphics)
    else:
        # Default: show solid color
        pen = graphics.create_pen(*current_color)
        graphics.set_pen(pen)
        graphics.clear()
        su.update(graphics)


def check_buttons():
    """Check physical buttons for brightness adjustment"""
    if su.is_pressed(StellarUnicorn.SWITCH_BRIGHTNESS_UP):
        su.adjust_brightness(+0.05)
    if su.is_pressed(StellarUnicorn.SWITCH_BRIGHTNESS_DOWN):
        su.adjust_brightness(-0.05)


# Main program
print("Stellar Unicorn - Home Assistant Integration")
print("=" * 40)

# Show startup animation
graphics.set_pen(graphics.create_pen(0, 50, 100))
graphics.clear()
su.update(graphics)

# Connect to WiFi
wlan = connect_wifi()

# Sync time via NTP
sync_time()

# Setup MQTT
mqtt_client = MQTTClient(
    config.MQTT_CLIENT_ID,
    config.MQTT_BROKER,
    port=config.MQTT_PORT,
    user=config.MQTT_USER if config.MQTT_USER else None,
    password=config.MQTT_PASSWORD if config.MQTT_PASSWORD else None,
    keepalive=60
)

mqtt_client.set_callback(on_message)

print(f"Connecting to MQTT broker {config.MQTT_BROKER}...")
mqtt_client.connect()
print("MQTT connected!")

# Subscribe to command topics
mqtt_client.subscribe(config.MQTT_TOPIC_TEXT)
mqtt_client.subscribe(config.MQTT_TOPIC_BRIGHTNESS)
mqtt_client.subscribe(config.MQTT_TOPIC_COLOR)
mqtt_client.subscribe(config.MQTT_TOPIC_EFFECT)
mqtt_client.subscribe(config.MQTT_TOPIC_POWER)
mqtt_client.subscribe(config.MQTT_TOPIC_SENSORS)
print("Subscribed to topics")

# Publish availability and discovery
mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)
publish_ha_discovery()
publish_state()

# Set initial brightness
su.set_brightness(current_brightness)

print("Starting main loop...")
last_mqtt_check = time.ticks_ms()

while True:
    # Check for MQTT messages (non-blocking)
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_mqtt_check) > 100:
        try:
            mqtt_client.check_msg()
        except OSError as e:
            print(f"MQTT error: {e}, reconnecting...")
            try:
                mqtt_client.connect()
                mqtt_client.subscribe(config.MQTT_TOPIC_TEXT)
                mqtt_client.subscribe(config.MQTT_TOPIC_BRIGHTNESS)
                mqtt_client.subscribe(config.MQTT_TOPIC_COLOR)
                mqtt_client.subscribe(config.MQTT_TOPIC_EFFECT)
                mqtt_client.subscribe(config.MQTT_TOPIC_POWER)
                mqtt_client.subscribe(config.MQTT_TOPIC_SENSORS)
                mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)
            except:
                pass
        last_mqtt_check = current_time

    # Check physical buttons
    check_buttons()

    # Update display
    update_display()

    time.sleep(0.01)
