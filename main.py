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


def mqtt_subscribe_all():
    """Subscribe to all MQTT topics"""
    mqtt_client.subscribe(config.MQTT_TOPIC_TEXT)
    mqtt_client.subscribe(config.MQTT_TOPIC_BRIGHTNESS)
    mqtt_client.subscribe(config.MQTT_TOPIC_COLOR)
    mqtt_client.subscribe(config.MQTT_TOPIC_EFFECT)
    mqtt_client.subscribe(config.MQTT_TOPIC_POWER)
    mqtt_client.subscribe(config.MQTT_TOPIC_SENSORS)
    mqtt_client.subscribe(config.MQTT_TOPIC_DOOR_STATE)


print(f"Connecting to MQTT broker {config.MQTT_BROKER}...")
mqtt_client.connect()
print("MQTT connected!")

# Subscribe to command topics
mqtt_subscribe_all()
print("Subscribed to topics")

# Publish availability and discovery
mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)
publish_ha_discovery()
publish_state()

# Set initial brightness
su.set_brightness(state.brightness / 255.0)

# Connection state tracking
mqtt_connected = True
mqtt_reconnect_attempts = 0
mqtt_last_reconnect_attempt = 0
MQTT_RECONNECT_BASE_DELAY = 1000  # 1 second in milliseconds
MQTT_RECONNECT_MAX_DELAY = 60000  # 60 seconds max
MQTT_MAX_RECONNECT_ATTEMPTS = 10  # After this, reset to base delay
MQTT_PING_INTERVAL = 30000  # 30 seconds - send ping to keep connection alive
last_mqtt_ping = time.ticks_ms()
WIFI_CHECK_INTERVAL = 10000  # Check WiFi connection every 10 seconds
last_wifi_check = time.ticks_ms()


def check_wifi():
    """Check and reconnect WiFi if needed"""
    if not wlan.isconnected():
        print("WiFi disconnected, reconnecting...")
        try:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            max_wait = 10
            while max_wait > 0 and not wlan.isconnected():
                max_wait -= 1
                time.sleep(1)

            if wlan.isconnected():
                print(f"WiFi reconnected! IP: {wlan.ifconfig()[0]}")
                return True
            else:
                print("WiFi reconnection failed")
                return False
        except Exception as e:
            print(f"WiFi reconnection error: {e}")
            return False
    return True


def mqtt_subscribe_all():
    """Subscribe to all MQTT topics"""
    mqtt_client.subscribe(config.MQTT_TOPIC_TEXT)
    mqtt_client.subscribe(config.MQTT_TOPIC_BRIGHTNESS)
    mqtt_client.subscribe(config.MQTT_TOPIC_COLOR)
    mqtt_client.subscribe(config.MQTT_TOPIC_EFFECT)
    mqtt_client.subscribe(config.MQTT_TOPIC_POWER)
    mqtt_client.subscribe(config.MQTT_TOPIC_SENSORS)
    mqtt_client.subscribe(config.MQTT_TOPIC_DOOR_STATE)


def mqtt_reconnect():
    """Attempt to reconnect to MQTT broker with exponential backoff"""
    global mqtt_connected, mqtt_reconnect_attempts, mqtt_last_reconnect_attempt

    current_time = time.ticks_ms()

    # Calculate backoff delay
    if mqtt_reconnect_attempts >= MQTT_MAX_RECONNECT_ATTEMPTS:
        # Reset attempts after max to avoid overflow
        mqtt_reconnect_attempts = 0

    delay = min(MQTT_RECONNECT_BASE_DELAY * (2 ** mqtt_reconnect_attempts), MQTT_RECONNECT_MAX_DELAY)

    # Check if enough time has passed since last attempt
    if time.ticks_diff(current_time, mqtt_last_reconnect_attempt) < delay:
        return  # Not time to retry yet

    mqtt_last_reconnect_attempt = current_time
    mqtt_reconnect_attempts += 1

    print(f"MQTT reconnection attempt {mqtt_reconnect_attempts} (delay: {delay}ms)...")

    try:
        # Attempt to reconnect
        mqtt_client.connect()

        # Re-subscribe to all topics
        mqtt_subscribe_all()

        # Publish availability
        mqtt_client.publish(config.MQTT_TOPIC_AVAILABILITY, "online", retain=True)

        # Reset connection state
        mqtt_connected = True
        mqtt_reconnect_attempts = 0
        print("MQTT reconnected successfully!")

    except OSError as e:
        print(f"MQTT reconnect failed (OSError): {e}")
        mqtt_connected = False
    except Exception as e:
        print(f"MQTT reconnect failed (Exception): {e}")
        mqtt_connected = False


print("Starting main loop...")
last_mqtt_check = time.ticks_ms()

while True:
    current_time = time.ticks_ms()

    # Check WiFi connection periodically
    if time.ticks_diff(current_time, last_wifi_check) > WIFI_CHECK_INTERVAL:
        if not check_wifi():
            # WiFi is down, mark MQTT as disconnected
            mqtt_connected = False
        last_wifi_check = current_time

    # Check for MQTT messages (non-blocking)
    if time.ticks_diff(current_time, last_mqtt_check) > 100:
        if mqtt_connected:
            try:
                mqtt_client.check_msg()
            except OSError as e:
                print(f"MQTT error during check_msg: {e}")
                mqtt_connected = False
                mqtt_last_reconnect_attempt = 0  # Allow immediate first reconnect
            except Exception as e:
                print(f"MQTT unexpected error: {e}")
                mqtt_connected = False
                mqtt_last_reconnect_attempt = 0
        else:
            # Not connected, attempt reconnection (only if WiFi is up)
            if wlan.isconnected():
                mqtt_reconnect()

        last_mqtt_check = current_time

    # Proactive connection health check - send periodic ping
    if mqtt_connected and time.ticks_diff(current_time, last_mqtt_ping) > MQTT_PING_INTERVAL:
        try:
            mqtt_client.ping()
            last_mqtt_ping = current_time
        except OSError as e:
            print(f"MQTT ping failed: {e}")
            mqtt_connected = False
            mqtt_last_reconnect_attempt = 0
        except Exception as e:
            print(f"MQTT ping unexpected error: {e}")
            mqtt_connected = False
            mqtt_last_reconnect_attempt = 0

    # Check physical buttons
    check_buttons()

    # Update display
    update_display()

    time.sleep(0.01)
