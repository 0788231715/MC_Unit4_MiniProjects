#!/usr/bin/env python3
"""Generic simulated sensor publisher for Mini Project 4.3.
QoS 1, retained readings, and a Last Will on <area>/status (topic = plantX/lineY/<measurement>)."""
import argparse, random, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("topic", help="e.g. plant1/lineA/temperature")
ap.add_argument("--lo", type=float, default=60.0)
ap.add_argument("--hi", type=float, default=95.0)
ap.add_argument("--interval", type=float, default=2.0)
ap.add_argument("--qos", type=int, default=1)
ap.add_argument("--seed", type=int, default=None)
ap.add_argument("--lwt", action="store_true", help="register a Last Will on <line>/status for this node")
ap.add_argument("--no-retain", action="store_true")
ap.add_argument("--broker", default="127.0.0.1")
ap.add_argument("--port", type=int, default=1883)
a = ap.parse_args()
rnd = random.Random(a.seed)
parts = a.topic.split("/")
status_topic = "/".join(parts[:-1] + [f"status-{parts[-1]}"])
cid = "sensor-" + "-".join(parts)
ts = lambda: time.strftime("%H:%M:%S")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
if a.lwt:
    c.will_set(status_topic, "offline", qos=1, retain=True)
c.on_connect = lambda cl, u, f, rc, p: (cl.publish(status_topic, "online", qos=1, retain=True) if a.lwt else None,
                                        print(f"[{ts()}] {cid} connected (LWT {'ON' if a.lwt else 'off'})", flush=True))
c.connect(a.broker, a.port, keepalive=5); c.loop_start(); time.sleep(0.4)
try:
    while True:
        v = round(rnd.uniform(a.lo, a.hi), 2)
        c.publish(a.topic, str(v), qos=a.qos, retain=not a.no_retain)
        print(f"[{ts()}] {a.topic} = {v}", flush=True)
        time.sleep(a.interval)
except KeyboardInterrupt:
    c.disconnect(); c.loop_stop()
