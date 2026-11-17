#!/usr/bin/env python3
"""
Mini Project 4.1 Part B - LPWAN link-budget and battery-life comparison.

Scenario: 200 soil-moisture/temperature sensors over a 25 km^2 farm, 12-byte reading every
30 minutes, max sensor-to-gateway distance 8 km, target 5 years on a 3.6 V / 19,000 mAh primary
lithium cell, no cellular coverage nearby, preference to avoid per-device fees at 200-unit scale.

Link budget  : MCL = P_tx - sensitivity          (dB)
Path loss    : PL(d) = PL(d0) + 10 n log10(d/d0), PL(1 km) = 91.5 dB (~900 MHz), n = 3.5
Margin       : MCL - PL(d)
Energy       : mAh per cycle = I_tx * t_tx / 3600 + I_sleep * (interval - t_tx) / 3600
               years = capacity / (mAh per cycle * cycles per year)

ASSUMPTIONS (representative datasheet-class values, NOT measurements - edit them below):
  NB-IoT   : 23 dBm, -129 dBm sens.; ~3 s radio-on per report at ~120 mA avg (repetitions,
             attach/RRC/TAU overhead amortised, PSM sleep 5 uA)
  LTE-M    : 23 dBm, -125 dBm (CE mode B); ~5 s radio-on at ~200 mA avg (CE-B repetitions,
             higher peak current), sleep 8 uA (eDRX/PSM)
  LoRaWAN  : 14 dBm, -137 dBm (SF12/125 kHz); time-on-air for 12-byte payload ~1.32 s at
             ~44 mA, sleep 2 uA (Class A, no downlink listening beyond RX windows)
  5G RedCap: 23 dBm, -102 dBm (20 MHz carrier), ~2 s at ~250 mA, sleep 20 uA  (Lab task 5)
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CAPACITY_MAH = 19000.0
TARGET_YEARS = 5.0
INTERVAL_S = 30 * 60
CYCLES_PER_YEAR = 365 * 24 * 3600 / INTERVAL_S
SHELF_LIFE_YEARS = 15.0          # practical lithium primary-cell calendar limit (self-discharge)

TECH = {
    #  name        Ptx   sens   I_tx(mA) t_tx(s)  I_sleep(mA)
    "NB-IoT":    (23.0, -129.0, 120.0, 3.0, 0.005),
    "LTE-M":     (23.0, -125.0, 200.0, 5.0, 0.008),
    "LoRaWAN":   (14.0, -137.0,  44.0, 1.32, 0.002),
    "5G RedCap": (23.0, -102.0, 250.0, 2.0, 0.020),
}


def path_loss(d_km, n, pl0=91.5, d0=1.0):
    return pl0 + 10.0 * n * np.log10(d_km / d0)


def evaluate(d_km=8.0, n=3.5, include_redcap=False):
    pl = path_loss(d_km, n)
    out = {}
    for name, (ptx, sens, itx, ttx, isl) in TECH.items():
        if name == "5G RedCap" and not include_redcap:
            continue
        mcl = ptx - sens
        mah_cycle = itx * ttx / 3600.0 + isl * (INTERVAL_S - ttx) / 3600.0
        annual = mah_cycle * CYCLES_PER_YEAR
        years = CAPACITY_MAH / annual
        out[name] = dict(mcl=mcl, pl=pl, margin=mcl - pl, mah_cycle=mah_cycle,
                         annual_mah=annual, years=years,
                         eff_years=min(years, SHELF_LIFE_YEARS))
    return pl, out


def print_table(pl, res, title):
    print(title)
    print(f"path loss at the evaluated distance = {pl:.1f} dB")
    print(f"{'technology':<11}{'MCL(dB)':>9}{'margin(dB)':>12}{'mAh/cycle':>11}{'mAh/year':>10}"
          f"{'years':>8}{'>=5y?':>7}{'link OK?':>10}")
    for k, v in res.items():
        print(f"{k:<11}{v['mcl']:9.1f}{v['margin']:12.1f}{v['mah_cycle']:11.4f}{v['annual_mah']:10.0f}"
              f"{v['years']:8.1f}{'yes' if v['years'] >= TARGET_YEARS else 'NO':>7}"
              f"{'yes' if v['margin'] > 0 else 'NO':>10}")
    print()


def main():
    print(f"Cycles per year = {CYCLES_PER_YEAR:.0f}   battery = {CAPACITY_MAH:.0f} mAh   target = {TARGET_YEARS} years\n")
    pl, res = evaluate()
    print_table(pl, res, "=== Part B: assigned scenario (d = 8 km, n = 3.5) ===")
    print(f"Note: LoRaWAN calculated life exceeds the ~{SHELF_LIFE_YEARS:.0f}-year practical cell shelf life; "
          f"the cell, not the radio, becomes the limit.\n")

    print("=== Lab task 5: add 5G RedCap ===")
    pl, res_rc = evaluate(include_redcap=True)
    print_table(pl, res_rc, "with RedCap")

    print("=== Lab task 6: sensitivity to the path-loss exponent n ===")
    print(f"{'n':>5}{'PL(8km)':>9}" + "".join(f"{k:>12}" for k in res_rc))
    sens_rows = []
    for n in (2.5, 3.0, 3.5, 4.0, 4.5):
        pl, r = evaluate(n=n, include_redcap=True)
        print(f"{n:5.1f}{pl:9.1f}" + "".join(f"{v['margin']:12.1f}" for v in r.values()))
        sens_rows.append((n, pl, {k: v['margin'] for k, v in r.items()}))
    # largest d at which each technology still closes the link (margin = 0), n=3.5 and n=4.0
    print("\nMaximum range (km) where margin = 0:")
    print(f"{'n':>5}" + "".join(f"{k:>12}" for k in res_rc))
    for n in (3.5, 4.0):
        dmax = [10 ** ((v["mcl"] - 91.5) / (10 * n)) for v in res_rc.values()]
        print(f"{n:5.1f}" + "".join(f"{d:12.1f}" for d in dmax))

    print("\n=== Lab task 4: fleet-tracked shipping container across an ocean ===")
    print("Distance to the nearest terrestrial base station in mid-ocean is hundreds of km; with the")
    print("same model PL(500 km) = %.1f dB, far beyond every MCL above (max %.0f dB):" % (path_loss(500, 3.5), max(v['mcl'] for v in res_rc.values())))
    print("the link-budget sum is not merely 'tight' - there is no terrestrial network to budget against.")
    print("The decision hinges on non-radio axes: satellite/NTN availability, roaming agreements,")
    print("store-and-forward at ports, device cost and mobility - not on a single-distance margin.\n")

    # outputs
    with open(os.path.join(HERE, "link_budget_results.json"), "w") as f:
        json.dump({"assigned": res, "with_redcap": res_rc,
                   "n_sensitivity": [{"n": a, "pl": b, "margins": c} for a, b, c in sens_rows]}, f, indent=2)

    # simple recommendation text
    ok = {k: v for k, v in res.items() if v["margin"] > 0 and v["years"] >= TARGET_YEARS}
    print("Technologies meeting BOTH margin>0 and >=5 years:", ", ".join(ok) if ok else "none")
    print("Qualitative axes (Section 4.3): no cellular coverage nearby -> NB-IoT / LTE-M need an operator network")
    print("that does not exist on this farm; LoRaWAN needs only 1-2 self-owned gateways, no per-device fee.")
    print("RECOMMENDATION: LoRaWAN (SF12) with 1-2 farm-owned gateways.")


if __name__ == "__main__":
    main()
