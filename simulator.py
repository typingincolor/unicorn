#!/usr/bin/env python3
"""
Stellar Unicorn Simulator
Simulates the 16x16 LED matrix display for testing without hardware.
Connects to MQTT and shows what the Unicorn would display.
"""

import json
import time
import threading
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_CLIENT_ID,
    MQTT_TOPIC_TEXT, MQTT_TOPIC_BRIGHTNESS, MQTT_TOPIC_COLOR,
    MQTT_TOPIC_EFFECT, MQTT_TOPIC_POWER, MQTT_TOPIC_STATE,
    MQTT_TOPIC_AVAILABILITY, MQTT_TOPIC_SENSORS, MQTT_TOPIC_DOOR_STATE
)
from core import WIDTH, HEIGHT, DisplayState, Renderer

# Display buffer - each pixel is (r, g, b)
display = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]

# Shared state
state = DisplayState()


def clear_display():
    """Clear the display buffer to black"""
    global display
    display = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]


def set_pixel(x, y, r, g, b):
    """Set a pixel in the display buffer"""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        # Apply brightness
        brightness = state.brightness / 255.0
        display[y][x] = (int(r * brightness), int(g * brightness), int(b * brightness))


def get_time():
    """Get current time as (hours, minutes) tuple"""
    t = time.localtime()
    return (t.tm_hour, t.tm_min)


# Create renderer with our callbacks
renderer = Renderer(state, set_pixel, clear_display, get_time)


def print_display():
    """Print the 16x16 display to terminal"""
    print("\033[2J\033[H", end="")

    print("🦄 STELLAR UNICORN SIMULATOR (16x16)")
    print("=" * 50)

    if not state.power:
        print("  [DISPLAY OFF]")
    else:
        brightness_pct = int(state.brightness / 255 * 100)
        r, g, b = state.color
        print(f"  Brightness: {brightness_pct}% | Color: RGB({r},{g},{b})")
        if state.show_sensors:
            print(f"  Mode: Sensor Status")
        elif state.effect != "none":
            print(f"  Mode: Effect ({state.effect})")
        elif state.text:
            print(f"  Mode: Text \"{state.text[:20]}\"")
        else:
            print(f"  Mode: Solid Color")

    print("=" * 50)

    # Top border
    print("  ┌" + "──" * WIDTH + "┐")

    # Display pixels
    for y in range(HEIGHT):
        print("  │", end="")
        for x in range(WIDTH):
            r, g, b = display[y][x]
            if r == 0 and g == 0 and b == 0:
                print("  ", end="")
            else:
                print(f"\033[48;2;{r};{g};{b}m  \033[0m", end="")
        print("│")

    # Bottom border
    print("  └" + "──" * WIDTH + "┘")
    print("\nPress Ctrl+C to exit")


def publish_state(client):
    """Publish current state to MQTT"""
    payload = {
        "state": "ON" if state.power else "OFF",
        "brightness": state.brightness,
        "color": {"r": state.color[0], "g": state.color[1], "b": state.color[2]},
        "effect": state.effect,
        "text": state.text
    }
    client.publish(MQTT_TOPIC_STATE, json.dumps(payload))


def on_connect(client, userdata, flags, rc, properties=None):
    """Called when connected to MQTT broker"""
    if rc == 0:
        client.subscribe(MQTT_TOPIC_TEXT)
        client.subscribe(MQTT_TOPIC_BRIGHTNESS)
        client.subscribe(MQTT_TOPIC_COLOR)
        client.subscribe(MQTT_TOPIC_EFFECT)
        client.subscribe(MQTT_TOPIC_POWER)
        client.subscribe(MQTT_TOPIC_SENSORS)
        client.subscribe(MQTT_TOPIC_DOOR_STATE)

        client.publish(MQTT_TOPIC_AVAILABILITY, "online", retain=True)
        publish_state(client)


def on_message(client, userdata, msg):
    """Handle incoming MQTT messages"""
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == MQTT_TOPIC_POWER:
        state.power = payload.lower() in ("on", "true", "1")

    elif topic == MQTT_TOPIC_BRIGHTNESS:
        try:
            state.brightness = int(payload)
        except ValueError:
            pass

    elif topic == MQTT_TOPIC_COLOR:
        try:
            r, g, b = [int(x) for x in payload.split(",")]
            state.color = (r, g, b)
        except (ValueError, IndexError):
            pass

    elif topic == MQTT_TOPIC_EFFECT:
        state.effect = payload.lower()
        if state.effect == "clock":
            state.show_sensors = True
            state.text = ""
            state.effect = "none"
        elif state.effect != "none":
            state.text = ""
            state.show_sensors = False

    elif topic == MQTT_TOPIC_TEXT:
        state.text = payload
        state.effect = "none"
        state.show_sensors = False
        state.text_scroll_pos = WIDTH

    elif topic == MQTT_TOPIC_SENSORS:
        try:
            state.sensors = json.loads(payload)
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
            state.sensors[door_name] = payload
            state.show_sensors = True
            state.text = ""
            state.effect = "none"

    publish_state(client)


def animation_loop(client):
    """Background thread for animations"""
    while True:
        renderer.render()
        print_display()
        time.sleep(0.05)  # 20 FPS


def main():
    print("🦄 Stellar Unicorn Simulator")
    print(f"   Connecting to {MQTT_BROKER}:{MQTT_PORT}...")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_CLIENT_ID + "_sim")

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        anim_thread = threading.Thread(target=animation_loop, args=(client,), daemon=True)
        anim_thread.start()

        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        client.publish(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)
        client.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
