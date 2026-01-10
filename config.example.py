# Space Unicorn - WiFi and MQTT Configuration
# Copy this file to config.py and edit with your settings

# WiFi Settings
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# MQTT Settings
MQTT_BROKER = "192.168.1.x"  # IP address of your Raspberry Pi running Mosquitto
MQTT_PORT = 1883
MQTT_USER = ""  # Leave empty if no authentication
MQTT_PASSWORD = ""  # Leave empty if no authentication
MQTT_CLIENT_ID = "stellar_unicorn"

# MQTT Topics - Home Assistant will publish to these
MQTT_TOPIC_PREFIX = "unicorn"
MQTT_TOPIC_TEXT = f"{MQTT_TOPIC_PREFIX}/text/set"
MQTT_TOPIC_BRIGHTNESS = f"{MQTT_TOPIC_PREFIX}/brightness/set"
MQTT_TOPIC_COLOR = f"{MQTT_TOPIC_PREFIX}/color/set"
MQTT_TOPIC_EFFECT = f"{MQTT_TOPIC_PREFIX}/effect/set"
MQTT_TOPIC_POWER = f"{MQTT_TOPIC_PREFIX}/power/set"
MQTT_TOPIC_SENSORS = f"{MQTT_TOPIC_PREFIX}/sensors/set"

# Door sensor topics (subscribe with wildcard)
MQTT_TOPIC_DOOR_STATE = "home/door/+/state"

# MQTT State Topics - Unicorn will publish state to these
MQTT_TOPIC_STATE = f"{MQTT_TOPIC_PREFIX}/state"
MQTT_TOPIC_AVAILABILITY = f"{MQTT_TOPIC_PREFIX}/availability"

# Home Assistant MQTT Discovery prefix
HA_DISCOVERY_PREFIX = "homeassistant"

# Timezone offset from UTC (hours)
# UK: 0 for GMT (winter), 1 for BST (summer)
# Set to None for automatic BST detection
TIMEZONE_OFFSET = None
