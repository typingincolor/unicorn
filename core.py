# Space Unicorn - Shared Core Module
# Works with both MicroPython (Pico) and CPython (simulator)

import math
import random

# Display dimensions
WIDTH = 16
HEIGHT = 16

# Available effects
EFFECTS = ["rainbow", "fire", "plasma", "sparkle", "matrix", "gradient"]


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


def measure_text(text):
    """Measure the pixel width of text"""
    width = 0
    for char in text.upper():
        if char in FONT:
            width += len(FONT[char][0]) + 1
        else:
            width += 4
    return width


def draw_char(set_pixel, char, x, y, r, g, b):
    """Draw a character at position x, y using set_pixel callback"""
    char = char.upper()
    if char not in FONT:
        return 4

    glyph = FONT[char]
    width = len(glyph[0])

    for row_idx, row in enumerate(glyph):
        for col_idx, pixel in enumerate(row):
            if pixel == '1':
                set_pixel(x + col_idx, y + row_idx, r, g, b)

    return width + 1


def draw_text(set_pixel, text, x, y, r, g, b):
    """Draw text starting at position x, y"""
    cursor_x = x
    for char in text:
        cursor_x += draw_char(set_pixel, char, cursor_x, y, r, g, b)


class DisplayState:
    """Shared display state"""
    def __init__(self):
        self.power = True
        self.brightness = 128
        self.color = (255, 255, 255)
        self.effect = "none"
        self.text = ""
        self.sensors = {}
        self.show_sensors = True

        # Animation state
        self.frame = 0
        self.text_scroll_pos = WIDTH
        self.sensor_scroll_pos = WIDTH

        # Effect-specific state
        self.heat = [[0 for _ in range(HEIGHT)] for _ in range(WIDTH)]
        self.sparkles = []
        self.drops = [{"y": random.randint(-HEIGHT, 0), "speed": random.uniform(0.1, 0.3)}
                      for _ in range(WIDTH)]


class Renderer:
    """Shared rendering logic - works with any display that provides set_pixel/clear"""

    def __init__(self, state, set_pixel, clear, get_time):
        """
        state: DisplayState instance
        set_pixel: function(x, y, r, g, b) to set a pixel
        clear: function() to clear display
        get_time: function() returning (hours, minutes) tuple
        """
        self.state = state
        self.set_pixel = set_pixel
        self.clear = clear
        self.get_time = get_time

    def render(self):
        """Main render function - call this each frame"""
        if not self.state.power:
            self.clear()
            return

        if self.state.show_sensors:
            self._render_sensors()
        elif self.state.effect == "rainbow":
            self._render_rainbow()
        elif self.state.effect == "fire":
            self._render_fire()
        elif self.state.effect == "plasma":
            self._render_plasma()
        elif self.state.effect == "matrix":
            self._render_matrix()
        elif self.state.effect == "sparkle":
            self._render_sparkle()
        elif self.state.effect == "gradient":
            self._render_gradient()
        elif self.state.text:
            self._render_text()
        else:
            self._render_solid()

        self.state.frame += 1

    def _render_clock(self):
        """Render clock display"""
        self.clear()
        hours, mins = self.get_time()

        hours_str = "{:02d}".format(hours)
        mins_str = "{:02d}".format(mins)

        # Muted teal color
        r, g, b = 0, 150, 120

        # Hours on top row (centered)
        hours_width = measure_text(hours_str)
        hours_x = (WIDTH - hours_width) // 2 + 1
        draw_text(self.set_pixel, hours_str, hours_x, 2, r, g, b)

        # Minutes on bottom row (centered)
        mins_width = measure_text(mins_str)
        mins_x = (WIDTH - mins_width) // 2 + 1
        draw_text(self.set_pixel, mins_str, mins_x, 9, r, g, b)

    def _render_sensors(self):
        """Render sensor display - red border if doors open, clock always shown"""
        # Build list of open doors
        open_doors = []
        for name, status in self.state.sensors.items():
            if status.lower() in ("open", "on", "true", "1"):
                open_doors.append(name.upper())

        # Always show clock
        self._render_clock()

        # Draw red border if any doors are open
        if open_doors:
            r, g, b = 255, 0, 0
            # Top and bottom edges
            for x in range(WIDTH):
                self.set_pixel(x, 0, r, g, b)
                self.set_pixel(x, HEIGHT - 1, r, g, b)
            # Left and right edges
            for y in range(HEIGHT):
                self.set_pixel(0, y, r, g, b)
                self.set_pixel(WIDTH - 1, y, r, g, b)

    def _render_text(self):
        """Render scrolling text"""
        self.clear()

        r, g, b = self.state.color
        text = self.state.text

        y_pos = (HEIGHT - 5) // 2
        draw_text(self.set_pixel, text, int(self.state.text_scroll_pos), y_pos, r, g, b)

        # Update scroll
        self.state.text_scroll_pos -= 0.4
        text_width = measure_text(text)
        if self.state.text_scroll_pos < -text_width:
            self.state.text_scroll_pos = WIDTH

    def _render_solid(self):
        """Render solid color"""
        r, g, b = self.state.color
        for y in range(HEIGHT):
            for x in range(WIDTH):
                self.set_pixel(x, y, r, g, b)

    def _render_rainbow(self):
        """Render rainbow effect"""
        for y in range(HEIGHT):
            for x in range(WIDTH):
                hue = (x * 20 + y * 20 + self.state.frame * 5) % 360
                r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
                self.set_pixel(x, y, r, g, b)

    def _render_fire(self):
        """Render fire effect"""
        heat = self.state.heat

        # Cool down
        for x in range(WIDTH):
            for y in range(HEIGHT):
                heat[x][y] = max(0, heat[x][y] - random.randint(0, 3))

        # Heat rises
        for x in range(WIDTH):
            for y in range(HEIGHT - 1, 0, -1):
                heat[x][y] = (heat[x][y - 1] +
                             heat[(x - 1) % WIDTH][y - 1] +
                             heat[(x + 1) % WIDTH][y - 1]) // 3

        # Ignite bottom
        for x in range(WIDTH):
            if random.random() < 0.7:
                heat[x][0] = min(255, heat[x][0] + random.randint(160, 255))

        # Render
        for y in range(HEIGHT):
            for x in range(WIDTH):
                h = heat[x][HEIGHT - 1 - y]
                if h < 64:
                    self.set_pixel(x, y, h * 4, 0, 0)
                elif h < 128:
                    self.set_pixel(x, y, 255, (h - 64) * 4, 0)
                elif h < 192:
                    self.set_pixel(x, y, 255, 255, (h - 128) * 4)
                else:
                    self.set_pixel(x, y, 255, 255, 255)

    def _render_plasma(self):
        """Render plasma effect"""
        t = self.state.frame * 0.1

        for y in range(HEIGHT):
            for x in range(WIDTH):
                v1 = math.sin(x * 0.5 + t)
                v2 = math.sin((y * 0.5 + t) * 0.5)
                v3 = math.sin((x * 0.3 + y * 0.3 + t) * 0.5)
                v4 = math.sin(math.sqrt((x - 8) ** 2 + (y - 8) ** 2) * 0.5 - t)

                v = (v1 + v2 + v3 + v4) / 4.0
                hue = int((v + 1) * 180) % 360
                r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
                self.set_pixel(x, y, r, g, b)

    def _render_matrix(self):
        """Render matrix effect"""
        self.clear()
        drops = self.state.drops

        for x in range(WIDTH):
            drop = drops[x]
            y = int(drop["y"])

            # Draw trail
            for i in range(8):
                trail_y = y - i
                if 0 <= trail_y < HEIGHT:
                    brightness = max(0, 255 - i * 30)
                    self.set_pixel(x, trail_y, 0, brightness, 0)

            # Move drop
            drop["y"] += drop["speed"]

            # Reset if off screen
            if drop["y"] > HEIGHT + 8:
                drop["y"] = random.randint(-8, -1)
                drop["speed"] = random.uniform(0.1, 0.4)

    def _render_sparkle(self):
        """Render sparkle effect"""
        self.clear()
        sparkles = self.state.sparkles

        # Fade existing sparkles
        new_sparkles = []
        for sparkle in sparkles:
            sparkle["brightness"] -= 0.1
            if sparkle["brightness"] > 0:
                new_sparkles.append(sparkle)
        self.state.sparkles = new_sparkles

        # Add new sparkles
        if random.random() < 0.3:
            self.state.sparkles.append({
                "x": random.randint(0, WIDTH - 1),
                "y": random.randint(0, HEIGHT - 1),
                "brightness": 1.0,
                "hue": random.randint(0, 360)
            })

        # Draw sparkles
        for sparkle in self.state.sparkles:
            r, g, b = hsv_to_rgb(sparkle["hue"], 0.5, sparkle["brightness"])
            self.set_pixel(sparkle["x"], sparkle["y"], r, g, b)

    def _render_gradient(self):
        """Render gradient effect"""
        t = self.state.frame * 2

        for y in range(HEIGHT):
            hue = (t + y * 20) % 360
            r, g, b = hsv_to_rgb(hue, 1.0, 0.8)
            for x in range(WIDTH):
                self.set_pixel(x, y, r, g, b)
