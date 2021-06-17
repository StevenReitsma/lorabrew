from fastapi import FastAPI
from typing import List, Dict
import struct
import requests
import json
from fastapi_utils.tasks import repeat_every
from influxdb import InfluxDBClient
from datetime import datetime, timezone


latest_message = {}
latest_message_timestamp = datetime.utcnow()

with open("secrets.env", 'r') as secret_file:
    secrets = json.loads(secret_file.read())


app = FastAPI(
    title="LoRa Brewfather Passthrough",
    description="This project receives metrics from KPN LoRa and forwards them to Brewfather.",
    version="1.0.0",
)


@app.post(
    "/brew",
    summary="Post metrics from KPN LoRa",
    description="This endpoint accepts byte arrays posted by KPN LoRa",
)
async def lora_brew(senml_records: List[Dict]):
    payload = get_payload_bytes(senml_records)

    if payload is None:
        return "No valid payload"

    global latest_message
    received_msg = unmarshal_payload(payload)
    print(received_msg)

    latest_message = received_msg

    # Send to influx
    try:
        influx_point = {
            "time": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "measurement": "brew",
            "fields": received_msg,
        }
        client = InfluxDBClient("influxdb", 8086, database="brew")
        client.write_points([influx_point])
    except Exception as e:
        print(f"Could not send to Influx: {e}")

    return "OK"


def get_payload_bytes(records: List[Dict]) -> bytes:
    for record in records:
        if "n" in record and "vs" in record:
            if record["n"] == "payload":
                return bytes.fromhex(record["vs"])

    return None


def unmarshal_payload(buf: bytes) -> Dict:
    # First we decode all signed shorts back to floats
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

    message = {}

    for key, factor in factor_dict:
        byte = buf[0:2]
        decoded = struct.unpack("<h", byte)[0] / factor
        message[key] = decoded

        buf = buf[2:]

    # Now we construct a single byte from the three remaining enums
    enum = struct.unpack("<B", buf)[0]
    message["U"] = "C" if enum & 64 == 64 else "F"
    message["m"] = (enum & 0x30) >> 4
    message["s"] = enum & 0xF

    return message


def marshal_to_brewfather(message):
    return {
        "name": "Lorabrew",
        "temp": message["b"],
        "aux_temp": message["f"],
        "ext_temp": message["r"],
        "temp_unit": message["U"],
        "gravity": message["g"],
        "gravity_unit": "G",
        "battery": message["v"],
    }


def send_to_brewfather(message):
    response = requests.post(
        f"http://log.brewfather.net/stream?id={secrets['brewfather_stream']}", json=message
    )
    print(response.text)


@app.on_event("startup")
@repeat_every(seconds=900, wait_first=True)
def periodic():
    global latest_message
    global latest_message_timestamp
    global last_sent_to_brewfather

    # Only send if there is a message
    if latest_message is not None and len(latest_message) > 0:
        brewfather_message = marshal_to_brewfather(latest_message)
        print(f"Sending {brewfather_message} to Brewfather")
        send_to_brewfather(brewfather_message)

        # Reset message buffer so we never send the same message twice
        latest_message = {}
