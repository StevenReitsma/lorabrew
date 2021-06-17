import time
import json
import ubinascii as binascii
from network import WLAN
import machine

from lora import LoraSender
from webserver import WebServer


# Read keys from secret file
with open("secrets.env", "r") as secret_file:
    secrets = json.loads(secret_file.read())

dev_eui = binascii.unhexlify(secrets["dev_eui"])
app_eui = binascii.unhexlify(secrets["app_eui"])
app_key = binascii.unhexlify(secrets["app_key"])

# Start WLAN station (connect to BrewPiLess)
wlan = WLAN()
wlan.init(mode=WLAN.STA)
wlan.ifconfig(
    id=0,
    config=(secrets["ip"], "255.255.255.0", secrets["gateway"], secrets["gateway"]),
)
wlan.connect(ssid=secrets["ssid"], auth=(WLAN.WPA2, secrets["wifi_password"]))

# If we cannot connect to wifi, restart after 30 seconds
counter = 0
while not wlan.isconnected():
    if counter > 30:
        machine.reset()
    counter += 1
    time.sleep(1)

print(
    "[INFO] WiFi connected succesfully (IP, Subnet, Gateway, DNS): "
    + ", ".join(wlan.ifconfig())
)

# Define a watchdog that restarts the device if it's not fed every 2 minutes
wdt = machine.WDT(timeout=120000)
wdt.feed()

# Connect to KPN LoRa
lora_sender = LoraSender(dev_eui, app_eui, app_key)
lora_sender.join()

# Start web server
webserver = WebServer(lora_sender.set_metrics, wdt)
webserver.start()

# Stop web server and LoRa sender if CTRL+C event is given
try:
    wifi_counter = 0
    while True:
        # Restart if we lose wifi connection for more than 10 seconds
        if not wlan.isconnected():
            if wifi_counter > 10:
                machine.reset()
            wifi_counter += 1
        else:
            wifi_counter = 0

        time.sleep(1)
except KeyboardInterrupt:
    webserver.stop()
    lora_sender.stop()
    wdt.init(timeout=9999999)
