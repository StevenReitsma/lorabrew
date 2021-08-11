import time
import socket
import ustruct as struct
from network import LoRa
from machine import Timer
import json


class LoraSender:
    def __init__(self, dev_eui, app_eui, app_key, interval=150.0):
        self.dev_eui = dev_eui
        self.app_eui = app_eui
        self.app_key = app_key

        self.alarm = Timer.Alarm(
            self._send_metrics_to_lora, float(interval), periodic=True
        )
        self.latest_metrics = {}

    def join(self):
        self.lora = LoRa()
        self.lora.init(mode=LoRa.LORAWAN, region=LoRa.EU868, adr=True)

        # First check if there are session keys stored in NVRAM
        self.lora.nvram_restore()

        # If not, join using OTAA and create new keys
        if not self.lora.has_joined():
            print("[INFO] No existing keys, joining LoRa with OTAA...")
            self.lora.join(
                LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0
            )

        while not self.lora.has_joined():
            time.sleep(1)

        print("[INFO] Joined LoRa")

        # Save keys (new or pre-existing) to NVRAM
        self.lora.nvram_save()

        # Create communication socket
        self.socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

        # Send boot message to LoRa
        self.send_message(bytes([0x13, 0x37]))

    def send_message(self, send_bytes):
        self.socket.setblocking(True)
        self.socket.send(send_bytes)
        self.socket.setblocking(False)

        # Save message counter
        self.lora.nvram_save()

    def set_metrics(self, metrics):
        self.latest_metrics = metrics

    def stop(self):
        self.alarm.cancel()

    def _send_metrics_to_lora(self, _):
        if self.latest_metrics is None or len(self.latest_metrics) == 0:
            return

        msg = self._marshal_latest_metrics()
        self.send_message(msg)
        print("[INFO] Sent message to LoRa: " + json.dumps(self.latest_metrics))

        # Empty message buffer so we never send the same BPL message twice
        self.latest_metrics = {}

    def _marshal_latest_metrics(self):
        factor_dict = [
            ("b", 300.0),
            ("B", 300.0),
            ("f", 300.0),
            ("F", 300.0),
            ("r", 300.0),
            ("g", 10000.0),
            ("t", 150.0),
            ("a", 300.0),
            ("v", 3000.0),
        ]
        msg = b""

        # First encode all floats into 2-bit signed shorts
        for key, factor in factor_dict:
            if self.latest_metrics[key] is None:
                self.latest_metrics[key] = 0
            encoded = struct.pack("<h", int(self.latest_metrics[key] * factor))
            msg += encoded

        # Construct a single byte from the three remaining enums
        msg += struct.pack(
            "<B",
            (int(self.latest_metrics["U"] == "C") << 6)
            | (int(self.latest_metrics["m"]) << 4)
            | int(self.latest_metrics["s"]),
        )
        return msg
