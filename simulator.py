#!/usr/bin/env python3
"""
Stellar Unicorn Simulator
Simulates the 16x16 LED matrix display for testing without hardware.
Connects to MQTT and shows what the Unicorn would display.
"""

import json
import time
import math
import random
import threading
import paho.mqtt.client as mqtt

# Import config
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_CLIENT_ID,
    MQTT_TOPIC_TEXT, MQTT_TOPIC_BRIGHTNESS, MQTT_TOPIC_COLOR,
    MQTT_TOPIC_EFFECT, MQTT_TOPIC_POWER, MQTT_TOPIC_STATE,
    MQTT_TOPIC_AVAILABILITY, MQTT_TOPIC_SENSORS, HA_DISCOVERY_PREFIX
)

# Display dimensions
WIDTH = 16
HEIGHT = 16

# Display buffer - each pixel is (r, g, b)
display = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]

# State
state = {
    "power": True,
    "brightness": 128,
    "color": (255, 255, 255),
    "effect": "none",
    "text": "",
    "sensors": {},
    "show_sensors": True  # Default to clock/sensor mode
}

# Animation state
animation_frame = 0
text_scroll_pos = WIDTH
sensor_scroll_pos = WIDTH

# Fire effect state
heat = [[0 for _ in range(HEIGHT)] for _ in range(WIDTH)]



def clear_display():
    """Clear the display buffer to black"""
    global display
    display = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]


def set_pixel(x, y, r, g, b):
    """Set a pixel in the display buffer"""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        # Apply brightness
        brightness = state["brightness"] / 255.0
        display[y][x] = (int(r * brightness), int(g * brightness), int(b * brightness))


def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB (h: 0-360, s: 0-1, v: 0-1)"""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)


# Simple 4x5 font for display
FONT = {
    'A': ["0110", "1001", "1111", "1001", "1001"],
    'B': ["1110", "1001", "1110", "1001", "1110"],
    'C': ["0111", "1000", "1000", "1000", "0111"],
    'D': ["1110", "1001", "1001", "1001", "1110"],
    'E': ["1111", "1000", "1110", "1000", "1111"],
    'F': ["1111", "1000", "1110", "1000", "1000"],
    'G': ["0111", "1000", "1011", "1001", "0111"],
    'H': ["1001", "1001", "1111", "1001", "1001"],
    'I': ["111", "010", "010", "010", "111"],
    'J': ["0011", "0001", "0001", "1001", "0110"],
    'K': ["1001", "1010", "1100", "1010", "1001"],
    'L': ["1000", "1000", "1000", "1000", "1111"],
    'M': ["10001", "11011", "10101", "10001", "10001"],
    'N': ["1001", "1101", "1011", "1001", "1001"],
    'O': ["0110", "1001", "1001", "1001", "0110"],
    'P': ["1110", "1001", "1110", "1000", "1000"],
    'Q': ["0110", "1001", "1001", "1011", "0111"],
    'R': ["1110", "1001", "1110", "1010", "1001"],
    'S': ["0111", "1000", "0110", "0001", "1110"],
    'T': ["11111", "00100", "00100", "00100", "00100"],
    'U': ["1001", "1001", "1001", "1001", "0110"],
    'V': ["10001", "10001", "01010", "01010", "00100"],
    'W': ["10001", "10001", "10101", "11011", "10001"],
    'X': ["1001", "1001", "0110", "1001", "1001"],
    'Y': ["10001", "01010", "00100", "00100", "00100"],
    'Z': ["1111", "0001", "0110", "1000", "1111"],
    '0': ["0110", "1001", "1001", "1001", "0110"],
    '1': ["010", "110", "010", "010", "111"],
    '2': ["1110", "0001", "0110", "1000", "1111"],
    '3': ["1110", "0001", "0110", "0001", "1110"],
    '4': ["1001", "1001", "1111", "0001", "0001"],
    '5': ["1111", "1000", "1110", "0001", "1110"],
    '6': ["0110", "1000", "1110", "1001", "0110"],
    '7': ["1111", "0001", "0010", "0100", "0100"],
    '8': ["0110", "1001", "0110", "1001", "0110"],
    '9': ["0110", "1001", "0111", "0001", "0110"],
    ' ': ["00", "00", "00", "00", "00"],
    '!': ["1", "1", "1", "0", "1"],
    ':': ["0", "1", "0", "1", "0"],
    '-': ["000", "000", "111", "000", "000"],
    '.': ["0", "0", "0", "0", "1"],
    '?': ["0110", "1001", "0010", "0000", "0010"],
}


def draw_char(char, x, y, r, g, b):
    """Draw a character at position x, y"""
    char = char.upper()
    if char not in FONT:
        return 4  # Default width for unknown chars

    glyph = FONT[char]
    width = len(glyph[0])

    for row_idx, row in enumerate(glyph):
        for col_idx, pixel in enumerate(row):
            if pixel == '1':
                set_pixel(x + col_idx, y + row_idx, r, g, b)

    return width + 1  # Return width + spacing


def draw_text(text, x, y, r, g, b):
    """Draw text starting at position x, y"""
    cursor_x = x
    for char in text:
        cursor_x += draw_char(char, cursor_x, y, r, g, b)


def measure_text(text):
    """Measure the width of text"""
    width = 0
    for char in text.upper():
        if char in FONT:
            width += len(FONT[char][0]) + 1
        else:
            width += 4
    return width


def render_clock():
    """Render current time with hours on top, minutes on bottom"""
    clear_display()

    current_time = time.localtime()
    hours = current_time.tm_hour
    mins = current_time.tm_min

    hours_str = f"{hours:02d}"
    mins_str = f"{mins:02d}"

    # Muted teal color (brighter to account for brightness reduction)
    r, g, b = 0, 150, 120

    # Hours on top row (centered, shifted 1 pixel left)
    hours_width = measure_text(hours_str)
    hours_x = (WIDTH - hours_width) // 2 + 1
    draw_text(hours_str, hours_x, 2, r, g, b)

    # Minutes on bottom row (centered, shifted 1 pixel left)
    mins_width = measure_text(mins_str)
    mins_x = (WIDTH - mins_width) // 2 + 1
    draw_text(mins_str, mins_x, 9, r, g, b)


def render_sensors():
    """Render open doors as scrolling red text, or clock if all secure"""
    global sensor_scroll_pos

    # Build list of OPEN doors only
    open_doors = []
    for name, status in state["sensors"].items():
        is_open = status.lower() in ("open", "on", "true", "1")
        if is_open:
            open_doors.append(name.upper())

    # If all doors closed, show clock
    if not open_doors:
        render_clock()
        return

    clear_display()

    # Calculate total width of open door names
    total_width = 0
    for name in open_doors:
        total_width += measure_text(name + "  ")

    # Draw each open door name in RED
    y_pos = (HEIGHT - 5) // 2
    x_pos = int(sensor_scroll_pos)

    for name in open_doors:
        draw_text(name, x_pos, y_pos, 255, 0, 0)
        x_pos += measure_text(name + "  ")

    # Update scroll position
    sensor_scroll_pos -= 0.5  # Slightly faster for alerts

    if sensor_scroll_pos < -total_width:
        sensor_scroll_pos = WIDTH


def render_scrolling_text():
    """Render scrolling text to display"""
    global text_scroll_pos

    clear_display()

    r, g, b = state["color"]
    text = state["text"]

    # Draw text at scroll position
    y_pos = (HEIGHT - 5) // 2  # Center vertically
    draw_text(text, int(text_scroll_pos), y_pos, r, g, b)

    # Update scroll position every frame (at 20fps, 0.4 = ~8 pixels/sec)
    text_scroll_pos -= 0.4

    text_width = measure_text(text)
    if text_scroll_pos < -text_width:
        text_scroll_pos = WIDTH


def render_solid_color():
    """Render solid color to display"""
    r, g, b = state["color"]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            set_pixel(x, y, r, g, b)


def render_rainbow():
    """Render rainbow effect"""
    global animation_frame
    for y in range(HEIGHT):
        for x in range(WIDTH):
            hue = (x * 20 + y * 20 + animation_frame * 5) % 360
            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            set_pixel(x, y, r, g, b)
    animation_frame += 1


def render_fire():
    """Render fire effect"""
    global heat

    # Cool down
    for x in range(WIDTH):
        for y in range(HEIGHT):
            heat[x][y] = max(0, heat[x][y] - random.randint(0, 3))

    # Heat rises
    for x in range(WIDTH):
        for y in range(HEIGHT - 1, 0, -1):
            heat[x][y] = (heat[x][y - 1] + heat[(x - 1) % WIDTH][y - 1] + heat[(x + 1) % WIDTH][y - 1]) // 3

    # Ignite bottom
    for x in range(WIDTH):
        if random.random() < 0.7:
            heat[x][0] = min(255, heat[x][0] + random.randint(160, 255))

    # Render
    for y in range(HEIGHT):
        for x in range(WIDTH):
            h = heat[x][HEIGHT - 1 - y]
            if h < 64:
                set_pixel(x, y, h * 4, 0, 0)
            elif h < 128:
                set_pixel(x, y, 255, (h - 64) * 4, 0)
            elif h < 192:
                set_pixel(x, y, 255, 255, (h - 128) * 4)
            else:
                set_pixel(x, y, 255, 255, 255)


def render_plasma():
    """Render plasma effect"""
    global animation_frame
    t = animation_frame * 0.1

    for y in range(HEIGHT):
        for x in range(WIDTH):
            v1 = math.sin(x * 0.5 + t)
            v2 = math.sin((y * 0.5 + t) * 0.5)
            v3 = math.sin((x * 0.3 + y * 0.3 + t) * 0.5)
            v4 = math.sin(math.sqrt((x - 8) ** 2 + (y - 8) ** 2) * 0.5 - t)

            v = (v1 + v2 + v3 + v4) / 4.0
            hue = int((v + 1) * 180) % 360
            r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
            set_pixel(x, y, r, g, b)

    animation_frame += 1


def render_matrix():
    """Render matrix effect"""
    global animation_frame

    clear_display()

    random.seed(42)  # Consistent drops
    for x in range(WIDTH):
        drop_y = (animation_frame // 2 + random.randint(0, 20) * 3) % (HEIGHT + 8)
        for i in range(8):
            y = drop_y - i
            if 0 <= y < HEIGHT:
                brightness = max(0, 255 - i * 30)
                set_pixel(x, y, 0, brightness, 0)
        random.random()  # Advance RNG

    animation_frame += 1


def render_sparkle():
    """Render sparkle effect"""
    clear_display()

    for _ in range(8):
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        brightness = random.randint(100, 255)
        hue = random.randint(0, 360)
        r, g, b = hsv_to_rgb(hue, 0.5, brightness / 255)
        set_pixel(x, y, r, g, b)


def render_gradient():
    """Render gradient effect"""
    global animation_frame

    for y in range(HEIGHT):
        hue = (animation_frame * 2 + y * 20) % 360
        r, g, b = hsv_to_rgb(hue, 1.0, 0.8)
        for x in range(WIDTH):
            set_pixel(x, y, r, g, b)

    animation_frame += 1


def render_display():
    """Render current state to display buffer"""
    if not state["power"]:
        clear_display()
        return

    if state["show_sensors"]:
        render_sensors()
    elif state["effect"] == "rainbow":
        render_rainbow()
    elif state["effect"] == "fire":
        render_fire()
    elif state["effect"] == "plasma":
        render_plasma()
    elif state["effect"] == "matrix":
        render_matrix()
    elif state["effect"] == "sparkle":
        render_sparkle()
    elif state["effect"] == "gradient":
        render_gradient()
    elif state["text"]:
        render_scrolling_text()
    else:
        render_solid_color()


def print_display():
    """Print the 16x16 display to terminal"""
    # Clear screen and move cursor to top
    print("\033[2J\033[H", end="")

    print("🦄 STELLAR UNICORN SIMULATOR (16x16)")
    print("=" * 50)

    if not state["power"]:
        print("  [DISPLAY OFF]")
    else:
        brightness_pct = int(state["brightness"] / 255 * 100)
        r, g, b = state["color"]
        print(f"  Brightness: {brightness_pct}% | Color: RGB({r},{g},{b})")
        if state["show_sensors"]:
            print(f"  Mode: Sensor Status")
        elif state["effect"] != "none":
            print(f"  Mode: Effect ({state['effect']})")
        elif state["text"]:
            print(f"  Mode: Text \"{state['text'][:20]}\"")
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
                print("  ", end="")  # Black = empty
            else:
                # Use ANSI 24-bit color
                print(f"\033[48;2;{r};{g};{b}m  \033[0m", end="")
        print("│")

    # Bottom border
    print("  └" + "──" * WIDTH + "┘")
    print("\nPress Ctrl+C to exit")


def publish_state(client):
    """Publish current state to MQTT"""
    payload = {
        "state": "ON" if state["power"] else "OFF",
        "brightness": state["brightness"],
        "color": {
            "r": state["color"][0],
            "g": state["color"][1],
            "b": state["color"][2]
        },
        "effect": state["effect"],
        "text": state["text"]
    }
    client.publish(MQTT_TOPIC_STATE, json.dumps(payload))


def on_connect(client, userdata, flags, rc, properties=None):
    """Called when connected to MQTT broker"""
    if rc == 0:
        # Subscribe to command topics
        client.subscribe(MQTT_TOPIC_TEXT)
        client.subscribe(MQTT_TOPIC_BRIGHTNESS)
        client.subscribe(MQTT_TOPIC_COLOR)
        client.subscribe(MQTT_TOPIC_EFFECT)
        client.subscribe(MQTT_TOPIC_POWER)
        client.subscribe(MQTT_TOPIC_SENSORS)

        # Publish availability
        client.publish(MQTT_TOPIC_AVAILABILITY, "online", retain=True)

        # Publish initial state
        publish_state(client)


def on_message(client, userdata, msg):
    """Handle incoming MQTT messages"""
    global text_scroll_pos

    topic = msg.topic
    payload = msg.payload.decode()

    if topic == MQTT_TOPIC_POWER:
        state["power"] = payload.lower() in ("on", "true", "1")

    elif topic == MQTT_TOPIC_BRIGHTNESS:
        try:
            state["brightness"] = int(payload)
        except ValueError:
            pass

    elif topic == MQTT_TOPIC_COLOR:
        try:
            r, g, b = [int(x) for x in payload.split(",")]
            state["color"] = (r, g, b)
        except (ValueError, IndexError):
            pass

    elif topic == MQTT_TOPIC_EFFECT:
        state["effect"] = payload.lower()
        if state["effect"] == "clock":
            # Switch back to clock/sensor mode
            state["show_sensors"] = True
            state["text"] = ""
            state["effect"] = "none"
        elif state["effect"] != "none":
            state["text"] = ""
            state["show_sensors"] = False

    elif topic == MQTT_TOPIC_TEXT:
        state["text"] = payload
        state["effect"] = "none"
        state["show_sensors"] = False
        text_scroll_pos = WIDTH  # Reset scroll

    elif topic == MQTT_TOPIC_SENSORS:
        global sensor_scroll_pos
        try:
            state["sensors"] = json.loads(payload)
            state["show_sensors"] = True
            state["text"] = ""
            state["effect"] = "none"
            sensor_scroll_pos = WIDTH  # Reset scroll position
        except (ValueError, TypeError):
            pass

    publish_state(client)


def animation_loop(client):
    """Background thread for animations"""
    while True:
        render_display()
        print_display()
        time.sleep(0.05)  # 20 FPS


def main():
    print("🦄 Stellar Unicorn Simulator")
    print(f"   Connecting to {MQTT_BROKER}:{MQTT_PORT}...")

    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_CLIENT_ID + "_sim")

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    # Set last will for availability
    client.will_set(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Start animation thread
        anim_thread = threading.Thread(target=animation_loop, args=(client,), daemon=True)
        anim_thread.start()

        # Run MQTT loop
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        client.publish(MQTT_TOPIC_AVAILABILITY, "offline", retain=True)
        client.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
