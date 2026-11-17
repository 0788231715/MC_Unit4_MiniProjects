#!/usr/bin/env python3
"""Late-joining subscriber used to demonstrate retained messages (subscribes to plant1/#)."""
import sys, time
import paho.mqtt.client as mqtt
t0 = time.time()
ts = lambda: time.strftime("%H:%M:%S")
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="late-joiner")
c.on_connect = lambda cl, u, f, rc, p: (print(f"[{ts()}] LATE-JOINER connected, subscribing to plant1/#", flush=True), cl.subscribe("plant1/#", qos=1))
c.on_message = lambda cl, u, m: print(f"[{ts()}] LATE-JOINER got {m.topic} = {m.payload.decode()}  retained={bool(m.retain)}  (+{time.time()-t0:.2f}s after connect)", flush=True)
c.connect("127.0.0.1", 1883, 30); c.loop_start(); time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 3); c.loop_stop()
