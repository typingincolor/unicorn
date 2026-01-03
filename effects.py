# Space Unicorn - Visual Effects Module
# Fire, Rainbow, Plasma, and other animations for Stellar Unicorn 16x16

import time
import math
import random


class Effects:
    def __init__(self, su, graphics, width, height):
        self.su = su
        self.graphics = graphics
        self.width = width
        self.height = height
        self.available = ["rainbow", "fire", "plasma", "sparkle", "matrix", "gradient"]

        # Effect state
        self.frame = 0
        self.last_update = time.ticks_ms()

        # Fire effect state
        self.heat = [[0 for _ in range(height)] for _ in range(width)]

        # Matrix effect state
        self.drops = [{"y": random.randint(-height, 0), "speed": random.uniform(0.1, 0.3)}
                      for _ in range(width)]

        # Sparkle effect state
        self.sparkles = []

    def run(self, effect_name):
        """Run the specified effect"""
        if effect_name == "rainbow":
            self._rainbow()
        elif effect_name == "fire":
            self._fire()
        elif effect_name == "plasma":
            self._plasma()
        elif effect_name == "sparkle":
            self._sparkle()
        elif effect_name == "matrix":
            self._matrix()
        elif effect_name == "gradient":
            self._gradient()

        self.su.update(self.graphics)
        self.frame += 1

    def _hsv_to_rgb(self, h, s, v):
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

    def _rainbow(self):
        """Rainbow wave effect"""
        for x in range(self.width):
            for y in range(self.height):
                # Calculate hue based on position and time
                hue = (x * 20 + y * 20 + self.frame * 5) % 360
                r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)
                pen = self.graphics.create_pen(r, g, b)
                self.graphics.set_pen(pen)
                self.graphics.pixel(x, y)

        time.sleep(0.03)

    def _fire(self):
        """Fire effect - flames rising from bottom"""
        # Cool down every cell
        for x in range(self.width):
            for y in range(self.height):
                cooldown = random.randint(0, 3)
                self.heat[x][y] = max(0, self.heat[x][y] - cooldown)

        # Heat rises - move heat up
        for x in range(self.width):
            for y in range(self.height - 1, 0, -1):
                self.heat[x][y] = (
                    self.heat[x][y - 1] +
                    self.heat[(x - 1) % self.width][y - 1] +
                    self.heat[(x + 1) % self.width][y - 1]
                ) // 3

        # Add new heat at bottom
        for x in range(self.width):
            if random.random() < 0.7:
                self.heat[x][0] = min(255, self.heat[x][0] + random.randint(160, 255))

        # Convert heat to color and draw
        for x in range(self.width):
            for y in range(self.height):
                heat = self.heat[x][self.height - 1 - y]  # Flip Y for display

                # Fire color palette: black -> red -> orange -> yellow -> white
                if heat < 64:
                    r, g, b = heat * 4, 0, 0
                elif heat < 128:
                    r, g, b = 255, (heat - 64) * 4, 0
                elif heat < 192:
                    r, g, b = 255, 255, (heat - 128) * 4
                else:
                    r, g, b = 255, 255, 255

                pen = self.graphics.create_pen(r, g, b)
                self.graphics.set_pen(pen)
                self.graphics.pixel(x, y)

        time.sleep(0.05)

    def _plasma(self):
        """Plasma effect - animated sine wave patterns"""
        t = self.frame * 0.1

        for x in range(self.width):
            for y in range(self.height):
                # Multiple overlapping sine waves
                v1 = math.sin(x * 0.5 + t)
                v2 = math.sin((y * 0.5 + t) * 0.5)
                v3 = math.sin((x * 0.3 + y * 0.3 + t) * 0.5)
                v4 = math.sin(math.sqrt((x - 8) ** 2 + (y - 8) ** 2) * 0.5 - t)

                v = (v1 + v2 + v3 + v4) / 4.0

                # Map to hue
                hue = int((v + 1) * 180) % 360
                r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)

                pen = self.graphics.create_pen(r, g, b)
                self.graphics.set_pen(pen)
                self.graphics.pixel(x, y)

        time.sleep(0.03)

    def _sparkle(self):
        """Random sparkle effect"""
        # Clear with fade
        self.graphics.set_pen(self.graphics.create_pen(0, 0, 0))
        self.graphics.clear()

        # Fade existing sparkles
        new_sparkles = []
        for sparkle in self.sparkles:
            sparkle["brightness"] -= 0.1
            if sparkle["brightness"] > 0:
                new_sparkles.append(sparkle)
        self.sparkles = new_sparkles

        # Add new sparkles
        if random.random() < 0.3:
            self.sparkles.append({
                "x": random.randint(0, self.width - 1),
                "y": random.randint(0, self.height - 1),
                "brightness": 1.0,
                "hue": random.randint(0, 360)
            })

        # Draw sparkles
        for sparkle in self.sparkles:
            r, g, b = self._hsv_to_rgb(sparkle["hue"], 0.5, sparkle["brightness"])
            pen = self.graphics.create_pen(r, g, b)
            self.graphics.set_pen(pen)
            self.graphics.pixel(sparkle["x"], sparkle["y"])

        time.sleep(0.05)

    def _matrix(self):
        """Matrix-style falling code effect"""
        # Clear with slight fade for trails
        self.graphics.set_pen(self.graphics.create_pen(0, 0, 0))
        self.graphics.clear()

        for x in range(self.width):
            drop = self.drops[x]
            y = int(drop["y"])

            # Draw the trail
            for i in range(8):
                trail_y = y - i
                if 0 <= trail_y < self.height:
                    brightness = max(0, 255 - i * 30)
                    pen = self.graphics.create_pen(0, brightness, 0)
                    self.graphics.set_pen(pen)
                    self.graphics.pixel(x, trail_y)

            # Move drop down
            drop["y"] += drop["speed"]

            # Reset when off screen
            if drop["y"] > self.height + 8:
                drop["y"] = random.randint(-8, -1)
                drop["speed"] = random.uniform(0.1, 0.4)

        time.sleep(0.05)

    def _gradient(self):
        """Animated color gradient"""
        t = self.frame * 2

        for y in range(self.height):
            # Calculate gradient color
            hue = (t + y * 20) % 360
            r, g, b = self._hsv_to_rgb(hue, 1.0, 0.8)
            pen = self.graphics.create_pen(r, g, b)
            self.graphics.set_pen(pen)

            for x in range(self.width):
                self.graphics.pixel(x, y)

        time.sleep(0.05)
