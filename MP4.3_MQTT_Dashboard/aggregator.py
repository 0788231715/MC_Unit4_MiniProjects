#!/usr/bin/env python3
"""Mini Project 4.3 - aggregator / logger / alert engine using ONE wildcard subscription 'plant1/+/+'.

* timestamps and stores every reading in sample_log.csv
* keeps latest/min/max/count per topic and prints a summary table every SUMMARY_EVERY seconds
* independent per-topic threshold alerting (temperature and vibration thresholds differ; any single
  topic can be overridden in TOPIC_OVERRIDES)
* any NEW topic that matches plant1/+/+ is picked up automatically - no code change
"""
import argparse, csv, os, threading, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--broker", default="127.0.0.1"); ap.add_argument("--port", type=int, default=1883)
ap.add_argument("--summary-every", type=float, default=10.0)
ap.add_argument("--csv", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_log.csv"))
a = ap.parse_args()

THRESHOLDS = {"temperature": 88.0, "vibration": 7.5}          # by measurement type
TOPIC_OVERRIDES = {"plant1/lineB/temperature": 85.0}          # per-topic override (stricter on line B)
lock = threading.Lock()
state = {}                                                    # topic -> dict(latest, min, max, n, ts)
status = {}
ts = lambda: time.strftime("%H:%M:%S")
f = open(a.csv, "w", newline=""); w = csv.writer(f); w.writerow(["timestamp", "topic", "value", "retained"]); f.flush()


def threshold_for(topic):
    return TOPIC_OVERRIDES.get(topic, THRESHOLDS.get(topic.split("/")[-1]))


def on_connect(c, u, fl, rc, p):
    print(f"[{ts()}] AGGREGATOR connected; single wildcard subscription 'plant1/+/+' (QoS 1)", flush=True)
    c.subscribe("plant1/+/+", qos=1)


def on_message(c, u, m):
    topic, payload = m.topic, m.payload.decode()
    last = topic.split("/")[-1]
    if last.startswith("status"):
        with lock: status[topic] = payload
        print(f"[{ts()}] STATUS  {topic} = {payload}" + ("  <-- LWT / state change" if payload == "offline" else ""), flush=True)
        return
    try:
        v = float(payload)
    except ValueError:
        return
    new = topic not in state
    with lock:
        s = state.setdefault(topic, dict(latest=v, min=v, max=v, n=0, ts=ts()))
        s.update(latest=v, min=min(s["min"], v), max=max(s["max"], v), n=s["n"] + 1, ts=ts())
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), topic, v, int(m.retain)]); f.flush()
    if new:
        print(f"[{ts()}] NEW TOPIC discovered automatically: {topic}", flush=True)
    thr = threshold_for(topic)
    flag = "*** ALERT ***" if thr is not None and v > thr else "ok"
    print(f"[{ts()}] READING {topic} = {v}  (thr {thr}) {flag}" + (" [retained]" if m.retain else ""), flush=True)


def summary_loop():
    while True:
        time.sleep(a.summary_every)
        with lock:
            print(f"\n[{ts()}] ---------------- SUMMARY (latest value per topic) ----------------", flush=True)
            print(f"{'topic':<28}{'latest':>8}{'min':>8}{'max':>8}{'n':>5}{'thr':>7}  last-seen", flush=True)
            for t in sorted(state):
                s = state[t]
                print(f"{t:<28}{s['latest']:8.2f}{s['min']:8.2f}{s['max']:8.2f}{s['n']:5d}{str(threshold_for(t)):>7}  {s['ts']}", flush=True)
            print(f"status: {status}\n", flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="plant1-aggregator")
c.on_connect, c.on_message = on_connect, on_message
c.connect(a.broker, a.port, 60)
threading.Thread(target=summary_loop, daemon=True).start()
try:
    c.loop_forever()
except KeyboardInterrupt:
    pass
