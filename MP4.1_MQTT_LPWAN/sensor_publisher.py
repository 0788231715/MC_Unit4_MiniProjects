#!/usr/bin/env python3
"""Mini Project 4.1 Part A - simulated temperature sensor (MQTT publisher).

* client id "line3-temp-sensor", publishes a random value 60..95 every 5 s at QoS 1
* Last Will and Testament registered BEFORE connect: topic factory/line3/status, "offline",
  QoS 1, retained
* publishes "online" (retained) right after connecting
* every reading is published with retain=True, so a late subscriber always gets the LAST known
  reading (retaining only the first reading would leave a stale value on the broker)
"""
import argparse, random, sys, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--broker", default="127.0.0.1")
ap.add_argument("--port", type=int, default=1883)
ap.add_argument("--client-id", default="line3-temp-sensor")
ap.add_argument("--topic", default="factory/line3/temperature")
ap.add_argument("--status-topic", default="factory/line3/status")
ap.add_argument("--interval", type=float, default=5.0)
ap.add_argument("--qos", type=int, default=1)
ap.add_argument("--lo", type=float, default=60.0)
ap.add_argument("--hi", type=float, default=95.0)
ap.add_argument("--keepalive", type=int, default=5)
ap.add_argument("--seed", type=int, default=None)
ap.add_argument("--count", type=int, default=0, help="stop after N readings (0 = run forever)")
args = ap.parse_args()
rnd = random.Random(args.seed)


def ts():
    return time.strftime("%H:%M:%S")


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[{ts()}] connected to broker (reason: {reason_code})", flush=True)
    client.publish(args.status_topic, "online", qos=1, retain=True)
    print(f"[{ts()}] published status 'online' (retained) -> {args.status_topic}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id)
client.on_connect = on_connect
client.will_set(args.status_topic, payload="offline", qos=1, retain=True)   # LWT - before connect
client.connect(args.broker, args.port, keepalive=args.keepalive)
client.loop_start()

n = 0
try:
    time.sleep(0.5)
    while True:
        value = round(rnd.uniform(args.lo, args.hi), 1)
        info = client.publish(args.topic, f"{value}", qos=args.qos, retain=True)
        n += 1
        print(f"[{ts()}] PUBLISH #{n} {args.topic} = {value} (QoS {args.qos}, retain=True)", flush=True)
        if args.count and n >= args.count:
            break
        time.sleep(args.interval)
except KeyboardInterrupt:
    pass
# clean shutdown: a clean DISCONNECT does NOT trigger the Last Will
client.disconnect(); client.loop_stop()
print(f"[{ts()}] clean disconnect - LWT will NOT fire", flush=True)
