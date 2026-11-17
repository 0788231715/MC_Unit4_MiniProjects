#!/usr/bin/env python3
"""
Mini Project 4.2 - Rule-based IoT connectivity technology selector.

Candidates : NB-IoT, LTE-M, LoRaWAN, 5G RedCap, Short-range (BLE / Zigbee)
Axes (Section 4.3): data rate, coverage depth/range, battery life, mobility,
                    infrastructure ownership, cost per device at scale.

HOW IT WORKS (fully traceable - every number is in a table below)
1. CAPABILITY matrix  CAP[tech][axis]  in 0..5   (5 = strongest on that axis)
   transcribed from typical 3GPP / LoRa Alliance / Bluetooth SIG figures (see notes per axis).
2. REQUIREMENT mapping: user inputs -> 0..5 'need' level on the same scale.
3. Per-axis fit      fit = 5                      if cap >= need
                           max(0, 5 - 2*(need-cap)) otherwise     (a shortfall of 1 step costs 2 points)
   Ownership axis uses a lookup table (OWN_FIT) instead, because it is a preference, not a level.
4. Weighted sum       score = 100 * sum(w_i * fit_i) / (5 * sum(w_i))
5. Constraint rules   R1..R6 add penalties/exclusions for cases a plain sum handles poorly.
6. Justification      names the two best-fitting axes, the weakest axis, and every rule that fired.

NOTE: capability scores are authored from public specifications and typical figures. If your
Section 4.2 / 4.3 comparison tables differ, edit CAP below - nothing else needs to change.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TECHS = ["NB-IoT", "LTE-M", "LoRaWAN", "5G RedCap", "BLE/Zigbee"]
AXES = ["data_rate", "coverage", "battery", "mobility", "ownership", "cost"]

#                data  cover  batt  mobil  (own handled via OWN_FIT)  cost(5 = cheapest at scale)
CAP = {
    "NB-IoT":     dict(data_rate=2, coverage=5, battery=5, mobility=3, cost=3),   # ~30-60 kbps, MCL 164 dB, PSM, operator SIM fee
    "LTE-M":      dict(data_rate=4, coverage=4, battery=4, mobility=5, cost=2),   # ~1 Mbps, MCL 156 dB, handover + roaming, VoLTE
    "LoRaWAN":    dict(data_rate=1, coverage=4, battery=5, mobility=2, cost=4),   # 0.3-50 kbps, 15 km rural, no handover, no SIM fee
    "5G RedCap":  dict(data_rate=5, coverage=3, battery=2, mobility=5, cost=1),   # >=10 Mbps, cellular grid, hungrier modem
    "BLE/Zigbee": dict(data_rate=3, coverage=1, battery=4, mobility=2, cost=5),   # 0.25-2 Mbps, 10-100 m, cheapest silicon
}
# Ownership: preference -> fit (0..5).  'own' = wants self-owned infrastructure, 'operator' = happy to rent.
OWN_FIT = {
    "own":      {"NB-IoT": 1, "LTE-M": 1, "LoRaWAN": 5, "5G RedCap": 2, "BLE/Zigbee": 5},
    "operator": {"NB-IoT": 5, "LTE-M": 5, "LoRaWAN": 3, "5G RedCap": 5, "BLE/Zigbee": 2},
    "either":   {t: 4 for t in TECHS},
}
WEIGHTS = dict(data_rate=1.0, coverage=1.5, battery=1.2, mobility=1.0, ownership=1.0, cost=1.0)

COVERAGE_NEED = {"short_range": 1, "wide_area_cellular": 3, "long_range_rural": 4, "deep_indoor": 5}
MOBILITY_NEED = {"stationary": 1, "local": 2, "wide_area": 4, "global_roaming": 5}


def need_data(kbps):
    return 1 if kbps <= 5 else 2 if kbps <= 50 else 3 if kbps <= 500 else 4 if kbps <= 5000 else 5


def need_battery(years):
    return 1 if years <= 1 else 2 if years <= 3 else 3 if years <= 5 else 4 if years <= 10 else 5


def need_cost(devices, tier):
    base = {"low": 1, "medium": 3, "high": 5}[tier]               # budget tier: how cost-sensitive
    bonus = 1 if devices >= 10_000 else 0                          # scale amplifies per-device cost
    return min(5, base + bonus)


def fit(cap, need):
    return 5.0 if cap >= need else max(0.0, 5.0 - 2.0 * (need - cap))


def score(req, weights=WEIGHTS):
    need = dict(data_rate=need_data(req["kbps"]), coverage=COVERAGE_NEED[req["coverage"]],
                battery=need_battery(req["battery_years"]), mobility=MOBILITY_NEED[req["mobility"]],
                cost=need_cost(req["devices"], req["cost_tier"]))
    res = []
    for t in TECHS:
        fits = {a: fit(CAP[t][a], need[a]) for a in ("data_rate", "coverage", "battery", "mobility", "cost")}
        fits["ownership"] = float(OWN_FIT[req["ownership"]][t])
        raw = 100 * sum(weights[a] * fits[a] for a in AXES) / (5 * sum(weights.values()))
        adj, fired = raw, []
        # ---- constraint rules -------------------------------------------------------------
        if t == "LoRaWAN" and need["mobility"] >= 4:
            adj -= 20; fired.append("R1 -20: LoRaWAN has no cellular-style handover/global roaming")
        if t == "BLE/Zigbee" and need["coverage"] >= 3:
            adj *= 0.5; fired.append("R2 x0.5: short-range radio cannot cover a wide-area/rural/deep-indoor site alone")
        if t in ("NB-IoT", "LTE-M", "LoRaWAN", "5G RedCap") and need["coverage"] == 1:
            adj -= 10; fired.append("R3 -10: wide-area technology is overkill for a short-range-only need")
        if t in ("NB-IoT", "LTE-M", "5G RedCap") and req["ownership"] == "own" and req["devices"] >= 1000 \
                and need["cost"] >= 4:
            adj -= 10; fired.append("R4 -10: per-device operator fees at scale conflict with self-owned/cost-sensitive goal")
        if t in ("NB-IoT", "LoRaWAN") and need["data_rate"] >= 4:
            adj *= 0.3; fired.append("R5 x0.3: LPWAN cannot carry this data rate")
        if t == "5G RedCap" and need["battery"] >= 4:
            adj -= 10; fired.append("R6 -10: RedCap modem power is too high for a multi-year battery target")
        res.append(dict(tech=t, raw=raw, score=max(0.0, adj), fits=fits, rules=fired))
    res.sort(key=lambda r: -r["score"])
    return need, res


def justify(r, need):
    met = [a for a in AXES if r["fits"][a] == 5.0]
    short = [f"{a} ({r['fits'][a]:.0f}/5)" for a in AXES if r["fits"][a] < 5.0]
    txt = f"fully meets {len(met)}/6 axes ({', '.join(met) if met else 'none'})"
    txt += "; short on " + (", ".join(short) if short else "nothing")
    if r["rules"]:
        txt += "; rules: " + ", ".join(x.split(":")[0].split()[0] for x in r["rules"])
    return txt


def show(name, req, verbose=False):
    need, res = score(req)
    lines = [f"\n### {name}", "Needs (0..5): " + ", ".join(f"{k}={v}" for k, v in need.items())
             + f", ownership={req['ownership']}"]
    lines.append(f"{'rank':<5}{'technology':<12}{'score':>7}   justification")
    for i, r in enumerate(res, 1):
        lines.append(f"{i:<5}{r['tech']:<12}{r['score']:7.1f}   {justify(r, need)}")
    top = res[0]
    lines.append(f"RECOMMENDATION: {top['tech']}  (margin over runner-up: {top['score'] - res[1]['score']:.1f} points)")
    out = "\n".join(lines); print(out)
    return out, res


SCENARIOS = {
    "S1 Smart water meter (underground chamber, 15 yr, 100k units)": dict(
        kbps=0.5, coverage="deep_indoor", battery_years=15, mobility="stationary",
        ownership="operator", devices=100_000, cost_tier="high"),
    "S2 Fleet-tracked shipping container (global roaming)": dict(
        kbps=2, coverage="wide_area_cellular", battery_years=4, mobility="global_roaming",
        ownership="operator", devices=20_000, cost_tier="medium"),
    "S3 Factory-floor sensor network (vibration waveforms, AGVs)": dict(
        kbps=800, coverage="wide_area_cellular", battery_years=2, mobility="local",
        ownership="own", devices=800, cost_tier="medium"),
    "S4 Wearable health monitor (ECG, phone as gateway)": dict(
        kbps=100, coverage="short_range", battery_years=0.5, mobility="local",
        ownership="own", devices=50_000, cost_tier="high"),
    "S5 NEW: livestock collars on a remote 30,000-ha ranch (no cell coverage)": dict(
        kbps=1, coverage="long_range_rural", battery_years=3, mobility="local",
        ownership="own", devices=3_000, cost_tier="high"),
}

EXPECTED = {  # reasoning-based expectation used for validation (edit to match your Section 4.3 answers)
    "S1": "NB-IoT", "S2": "LTE-M", "S3": "5G RedCap", "S4": "BLE/Zigbee", "S5": "LoRaWAN"}


def interactive():
    print("Enter a new scenario (press Enter for the shown default)")
    def ask(q, d, cast=str):
        v = input(f"{q} [{d}]: ").strip(); return cast(v) if v else d
    req = dict(kbps=ask("data rate kbps", 10, float),
               coverage=ask("coverage (short_range/wide_area_cellular/long_range_rural/deep_indoor)", "wide_area_cellular"),
               battery_years=ask("battery target years", 5, float),
               mobility=ask("mobility (stationary/local/wide_area/global_roaming)", "stationary"),
               ownership=ask("ownership (own/operator/either)", "either"),
               devices=ask("device count", 1000, int), cost_tier=ask("cost tier (low/medium/high)", "medium"))
    show("User scenario", req)


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        interactive(); sys.exit()
    print("CAPABILITY MATRIX (0-5)   " + "  ".join(f"{a:>10}" for a in AXES))
    for t in TECHS:
        print(f"{t:<24}" + "  ".join(f"{(CAP[t].get(a) if a != 'ownership' else OWN_FIT['own'][t]):>10}" for a in AXES)
              + "   (ownership column shows the 'own' preference fit)")
    print("\nWEIGHTS:", WEIGHTS)
    table = []
    for name, req in SCENARIOS.items():
        out, res = show(name, req)
        key = name.split()[0]
        table.append((name, res[0]["tech"], EXPECTED[key], res[1]["tech"]))
    print("\n\n=== VALIDATION: top pick versus expected (Section 4.3 reasoning) ===")
    print(f"{'scenario':<75}{'tool pick':<12}{'expected':<12}{'runner-up':<12}{'match'}")
    for n, p, e, r2 in table:
        print(f"{n:<75}{p:<12}{e:<12}{r2:<12}{'YES' if p == e else 'DIVERGES'}")
    # ---- sensitivity: weights
    print("\n=== S3 divergence check: what flips the factory-floor pick? ===")
    base = SCENARIOS["S3 Factory-floor sensor network (vibration waveforms, AGVs)"]
    for label, mod in (("as scored (800 kbps)", {}), ("video/inspection payload 8 Mbps", {"kbps": 8000}),
                       ("ownership 'either' (public or private network acceptable)", {"ownership": "either"})):
        _, r = score({**base, **mod})
        print(f"{label:<62}", [f"{x['tech']}:{x['score']:.0f}" for x in r[:3]])
    print("\n=== Weight sensitivity (S2 container) ===")
    for label, w in (("default", WEIGHTS), ("mobility x2", {**WEIGHTS, "mobility": 2.0}),
                     ("cost x2", {**WEIGHTS, "cost": 2.0}), ("battery x2", {**WEIGHTS, "battery": 2.0})):
        _, r = score(SCENARIOS["S2 Fleet-tracked shipping container (global roaming)"], w)
        print(f"{label:<12}", [f"{x['tech']}:{x['score']:.0f}" for x in r[:3]])
    with open(os.path.join(HERE, "results_table.json"), "w") as f:
        json.dump([dict(scenario=n, pick=p, expected=e, runner_up=r2) for n, p, e, r2 in table], f, indent=2)
