#!/usr/bin/env python3
"""Mini Project 4.1 Part A - alert subscriber using the wildcard factory/+/temperature."""
import argparse, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--broker", default="127.0.0.1")
ap.add_argument("--port", type=int, default=1883)
ap.add_argument("--client-id", default="alert-monitor")
ap.add_argument("--topic", default="factory/+/temperature")
ap.add_argument("--threshold", type=float, default=90.0)
args = ap.parse_args()


def ts():
    return time.strftime("%H:%M:%S")


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[{ts()}] ALERT-MONITOR connected, subscribed to wildcard '{args.topic}' QoS 1 "
          f"(threshold {args.threshold})", flush=True)
    client.subscribe(args.topic, qos=1)


def on_message(client, userdata, msg):
    try:
        v = float(msg.payload.decode())
    except ValueError:
        return                                   # ignore non-numeric payloads (e.g. status)
    if v > args.threshold:
        print(f"[{ts()}] *** ALERT *** {msg.topic} = {v} exceeds {args.threshold}", flush=True)
    else:
        print(f"[{ts()}] alert-monitor: {msg.topic} = {v} (ok)", flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
c.on_connect, c.on_message = on_connect, on_message
c.connect(args.broker, args.port, 60)
try:
    c.loop_forever()
except KeyboardInterrupt:
    pass
