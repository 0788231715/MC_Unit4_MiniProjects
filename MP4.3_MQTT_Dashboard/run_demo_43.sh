#!/usr/bin/env bash
cd "$(dirname "$0")"; mkdir -p logs; rm -f logs/*.log
ts(){ date +%H:%M:%S; }
mark(){ echo "[$(ts)] ===== $* =====" | tee -a logs/marks.log; }
mosquitto -c ../MP4.1_MQTT_LPWAN/mosquitto_local.conf >logs/broker.log 2>&1 & BROKER=$!
sleep 1
mark "1. start aggregator (single wildcard plant1/+/+) and three publishers"
python3 aggregator.py --summary-every 12 >logs/aggregator.log 2>&1 & AGG=$!
sleep 1
python3 sensor_node.py plant1/lineA/temperature --lo 60 --hi 95 --interval 2   --seed 5  --lwt >logs/pub_lineA_temp.log 2>&1 & P1=$!
python3 sensor_node.py plant1/lineA/vibration   --lo 1  --hi 9  --interval 3   --seed 8        >logs/pub_lineA_vib.log 2>&1 & P2=$!
python3 sensor_node.py plant1/lineB/temperature --lo 60 --hi 92 --interval 2.5 --seed 21       >logs/pub_lineB_temp.log 2>&1 & P3=$!
sleep 20
mark "2. late-joining subscriber: retained messages arrive immediately"
python3 late_subscriber.py 3 >logs/late_subscriber.log 2>&1
sleep 2
mark "3. add a NEW sensor topic plant1/lineB/vibration while running - aggregator code unchanged"
python3 sensor_node.py plant1/lineB/vibration --lo 1 --hi 9 --interval 3 --seed 2 >logs/pub_lineB_vib.log 2>&1 & P4=$!
sleep 12
mark "4. kill -9 the lineA temperature publisher (has LWT) - ungraceful termination"
kill -9 $P1; sleep 4
mark "5. final summary and shutdown"
sleep 6
kill $P2 $P3 $P4 $AGG $BROKER 2>/dev/null; sleep 0.5
cat logs/marks.log logs/aggregator.log logs/late_subscriber.log | sort -s -k1,1 > logs/sample_timeline.log
echo done
