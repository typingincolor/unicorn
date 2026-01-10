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
from core import WIDTH, HEIGHT, DisplayState, Renderer

# Initialize hardware
su = StellarUnicorn()
graphics = PicoGraphics(DISPLAY)

# Shared state
state = DisplayState()


# Display adapter functions for core.Renderer
def clear_display():
    """Clear the PicoGraphics display"""
    graphics.set_pen(graphics.create_pen(0, 0, 0))
    graphics.clear()


def set_pixel(x, y, r, g, b):
    """Set a pixel on PicoGraphics display"""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        pen = graphics.create_pen(r, g, b)
        graphics.set_pen(pen)
        graphics.pixel(x, y)


def get_time():
    """Get current time from RTC as (hours, minutes) tuple"""
    rtc = machine.RTC()
    dt = rtc.datetime()
    return (dt[4], dt[5])  # hours, minutes


# Create renderer with our callbacks
renderer = Renderer(state, set_pixel, clear_display, get_time)


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

        rtc = machine.RTC()
        rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

        print(f"Time synced: {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} (UTC{'+' if offset_hours >= 0 else ''}{offset_hours})")
        return True
    except Exception as e:
        print(f"NTP sync failed: {e}")
        return False


# MQTT callbacks
def on_message(topic, msg):
    topic = topic.decode()
    msg = msg.decode()

    print(f"MQTT: {topic} = {msg}")

    if topic == config.MQTT_TOPIC_TEXT:
        state.text = msg
        state.text_scroll_pos = WIDTH
        state.effect = "none"
        state.show_sensors = False

    elif topic == config.MQTT_TOPIC_BRIGHTNESS:
        try:
            state.brightness = int(msg)
            su.set_brightness(state.brightness / 255.0)
        except ValueError:
            pass

    elif topic == config.MQTT_TOPIC_COLOR:
        try:
            r, g, b = [int(x) for x in msg.split(",")]
            state.color = (r, g, b)
        except (ValueError, IndexError):
            pass

    elif topic == config.MQTT_TOPIC_EFFECT:
        state.effect = msg.lower()
        if state.effect == "clock":
            state.show_sensors = True
            state.text = ""
            state.effect = "none"
        elif state.effect != "none":
            state.text = ""
            state.show_sensors = False

    elif topic == config.MQTT_TOPIC_POWER:
        state.power = msg.lower() in ("on", "true", "1")
        if not state.power:
            clear_display()
            su.update(graphics)

    elif topic == config.MQTT_TOPIC_SENSORS:
        try:
            state.sensors = json.loads(msg)
            state.show_sensors = True
            state.text = ""
            state.effect = "none"
            state.sensor_scroll_pos = WIDTH
        except (ValueError, TypeError):
            pass

    elif topic.startswith("home/door/") and topic.endswith("/state"):
        # Parse door name from topic: home/door/<name>/state
        parts = topic.split("/")
        if len(parts) == 4:
            door_name = parts[2]
            state.sensors[door_name] = msg
            state.show_sensors = True
            state.text = ""
            state.effect = "none"

    publish_state()


def publish_state():
    """Publish current state to Home Assistant"""
    payload = {
        "state": "ON" if state.power else "OFF",
        "brightness": state.brightness,
        "color": {"r": state.color[0], "g": state.color[1], "b": state.color[2]},
        "effect": state.effect,
        "text": state.text
    }
    try:
        mqtt_client.publish(config.MQTT_TOPIC_STATE, json.dumps(payload))
    except:
        pass


def publish_ha_discovery():
    """Publish Home Assistant MQTT Discovery config"""
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


def update_display():
    """Update the display using shared renderer"""
    renderer.render()
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
mqtt_client.subscribe(config.MQTT_TOPIC_DOOR_STATE)
print("Subscribed to topics")

# Publish availability and discovery
mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)
publish_ha_discovery()
publish_state()

# Set initial brightness
su.set_brightness(state.brightness / 255.0)

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
                mqtt_client.subscribe(config.MQTT_TOPIC_DOOR_STATE)
                mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)
            except:
                pass
        last_mqtt_check = current_time

    # Check physical buttons
    check_buttons()

    # Update display
    update_display()

    time.sleep(0.01)
