#!/usr/bin/env python3
"""Mini Project 4.1 Part A - operator dashboard: prints a timestamped line per event."""
import argparse, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--broker", default="127.0.0.1")
ap.add_argument("--port", type=int, default=1883)
ap.add_argument("--client-id", default="dashboard")
ap.add_argument("--topics", nargs="+", default=["factory/line3/temperature", "factory/line3/status"])
args = ap.parse_args()


def ts():
    return time.strftime("%H:%M:%S")


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[{ts()}] DASHBOARD connected, subscribing to {args.topics} at QoS 1", flush=True)
    for t in args.topics:
        client.subscribe(t, qos=1)


def on_message(client, userdata, msg):
    tag = " (RETAINED - delivered immediately on subscribe)" if msg.retain else ""
    print(f"[{ts()}] DASHBOARD {msg.topic} = {msg.payload.decode()}{tag}", flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
c.on_connect, c.on_message = on_connect, on_message
c.connect(args.broker, args.port, 60)
try:
    c.loop_forever()
except KeyboardInterrupt:
    pass
