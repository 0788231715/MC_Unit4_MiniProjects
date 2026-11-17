#!/usr/bin/env bash
# Automated Part A demonstration (steps 8-10): normal operation, retained message on a late
# subscriber, and Last Will on an ungraceful publisher termination.
cd "$(dirname "$0")"; mkdir -p logs; rm -f logs/*.log
ts(){ date +%H:%M:%S; }
mosquitto -c mosquitto_local.conf >logs/broker.log 2>&1 & BROKER=$!
sleep 1
echo "[$(ts)] ===== STEP 8: start dashboard, alert monitor, then publisher =====" | tee -a logs/00_marks.log
python3 dashboard_subscriber.py >logs/dashboard.log 2>&1 & DASH=$!
python3 alert_subscriber.py     >logs/alert.log 2>&1 & ALERT=$!
sleep 1
python3 sensor_publisher.py --seed 14 >logs/publisher.log 2>&1 & PUB=$!
sleep 28
echo "[$(ts)] ===== STEP 9: stop dashboard and restart it (publisher keeps running) =====" | tee -a logs/00_marks.log
kill $DASH; sleep 1
python3 dashboard_subscriber.py --client-id dashboard-restarted >logs/dashboard_restarted.log 2>&1 & DASH2=$!
sleep 6
echo "[$(ts)] ===== STEP 10: kill -9 the publisher (ungraceful, no DISCONNECT sent) =====" | tee -a logs/00_marks.log
kill -9 $PUB; sleep 3
echo "[$(ts)] ===== STEP 10b: restart publisher, then FREEZE it with SIGSTOP (socket stays open) =====" | tee -a logs/00_marks.log
python3 sensor_publisher.py --seed 14 --count 5 >logs/publisher2.log 2>&1 & PUB2=$!
sleep 2.5; kill -STOP $PUB2
echo "[$(ts)] publisher frozen; broker must wait 1.5 x keep-alive (7.5 s) before issuing the LWT" | tee -a logs/00_marks.log
sleep 13; kill -9 $PUB2 2>/dev/null
kill $DASH2 $ALERT $BROKER 2>/dev/null; sleep 0.5
cat logs/00_marks.log logs/dashboard.log logs/dashboard_restarted.log logs/alert.log logs/publisher.log logs/publisher2.log \
 | sed 's/^\(\[[0-9:]*\]\)/\1/' | sort -s -k1,1 > logs/combined_timeline.log
echo "done: see logs/"
