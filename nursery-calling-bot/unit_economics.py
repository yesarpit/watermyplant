#!/usr/bin/env python3
"""Per-enquiry call cost and contribution model for the enquiry -> gardener calling workflow.

  ./unit_economics.py                  # scenario table (assumptions below)
  ./unit_economics.py --runs runs/     # actuals from real or mock run logs

Every rate is an input you can override; the defaults are tagged in UNIT_ECONOMICS.md with where
they came from (published price vs. estimate). Monte Carlo over the call funnel, fixed seed.
"""
import argparse
import json
import random
from pathlib import Path

# INR per connected minute, all-in (voice + LLM + telephony). See UNIT_ECONOMICS.md for derivation.
PROVIDERS = {
    "sarvam-rented-number": 3.0,     # ESTIMATE: STT 0.50 + TTS ~1.0 + LLM ~0.2 + telephony ~0.6 + margin
    "sarvam-pessimistic": 6.0,       # ESTIMATE: if the Voice Agents platform charges 2x components
    "self-hosted-pipecat+sarvam-apis+plivo": 2.3,  # ESTIMATE: components at list price, no platform fee
    "retell-gpt-4.1": 10.1,          # PUBLISHED: $0.055 voice + $0.045 LLM + $0.015 telephony, x 88 INR/USD
    "retell-gpt-4.1-mini": 7.3,      # PUBLISHED: $0.055 + $0.0128 + $0.015, x 88
}


def simulate(p, trials=20000, seed=7):
    rng = random.Random(seed)
    tot_min = tot_dials = found_any = found_want = 0
    for _ in range(trials):
        minutes = dials = 0
        # customer: up to N attempts
        reached = False
        for _ in range(p.customer_attempts):
            dials += 1
            if rng.random() < p.customer_connect:
                minutes += p.customer_minutes
                reached = True
                break
            minutes += p.unanswered_minutes
        if not reached or rng.random() > p.customer_confirms:
            tot_min += minutes; tot_dials += dials
            continue
        available, pending = 0, list(range(p.max_gardeners))
        for pass_no in range(p.gardener_attempts):
            unreached = []
            for _g in pending:
                if available >= p.want:
                    break
                dials += 1
                if rng.random() < p.gardener_connect:
                    minutes += p.gardener_minutes
                    if rng.random() < p.gardener_available:
                        available += 1
                else:
                    minutes += p.unanswered_minutes
                    unreached.append(_g)
            pending = unreached
        tot_min += minutes; tot_dials += dials
        found_any += available >= 1
        found_want += available >= p.want
    return {"minutes": tot_min / trials, "dials": tot_dials / trials,
            "p_offer": found_any / trials, "p_want": found_want / trials}


def table(p):
    s = simulate(p)
    revenue_if_booked = max(p.fee_per_visit * p.visits, p.min_revenue)
    print(f"Funnel: {s['dials']:.1f} dials and {s['minutes']:.1f} billable min per enquiry; "
          f"P(>=1 gardener offer) = {s['p_offer']:.0%}; P(>={p.want}) = {s['p_want']:.0%}")
    print(f"Revenue if booked: max(Rs {p.fee_per_visit} fee x {p.visits} visits, Rs {p.min_revenue} minimum) "
          f"= Rs {revenue_if_booked}; "
          f"booking rate given an offer = {p.booking_rate:.0%}\n")
    print(f"| Provider | Rs/min | Call cost / enquiry | Expected revenue / enquiry | Contribution / enquiry "
          f"| Break-even booking rate | Enquiries/month to cover Rs {p.fixed_monthly} fixed |")
    print("|---|---|---|---|---|---|---|")
    exp_rev = s["p_offer"] * p.booking_rate * revenue_if_booked
    for name, rate in PROVIDERS.items():
        cost = s["minutes"] * rate
        contrib = exp_rev - cost
        be = cost / (s["p_offer"] * revenue_if_booked) if s["p_offer"] else float("inf")
        need = f"{p.fixed_monthly / contrib:.0f}" if contrib > 0 else "never"
        print(f"| {name} | {rate:.1f} | Rs {cost:.1f} | Rs {exp_rev:.1f} | Rs {contrib:.1f} | {be:.0%} | {need} |")


def actuals(runs_dir):
    logs = [json.loads(f.read_text()) for f in Path(runs_dir).glob("*.json")]
    if not logs:
        print(f"no run logs in {runs_dir}")
        return
    cost = sum(l["metrics"]["call_cost_inr"] for l in logs)
    mins = sum(l["metrics"]["call_minutes"] for l in logs)
    placed = sum(l["metrics"]["calls_placed"] for l in logs)
    connected = sum(l["metrics"]["calls_connected"] for l in logs)
    with_offer = sum(1 for l in logs if l.get("offers"))
    print(f"{len(logs)} enquiries | {placed} calls, {connected} connected "
          f"({connected / placed:.0%} connect) | {mins:.1f} min | Rs {cost:.1f} "
          f"(Rs {cost / len(logs):.1f}/enquiry) | {with_offer} with >=1 offer")
    results = {}
    for l in logs:
        results[l.get("result")] = results.get(l.get("result"), 0) + 1
    for r, n in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {r}")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--runs", help="summarise actual run logs instead of the model")
    a.add_argument("--customer-connect", type=float, default=0.6)
    a.add_argument("--customer-attempts", type=int, default=3)
    a.add_argument("--customer-confirms", type=float, default=0.7)
    a.add_argument("--customer-minutes", type=float, default=2.5)
    a.add_argument("--gardener-connect", type=float, default=0.5)
    a.add_argument("--gardener-available", type=float, default=0.35)
    a.add_argument("--gardener-minutes", type=float, default=1.5)
    a.add_argument("--gardener-attempts", type=int, default=2)
    a.add_argument("--unanswered-minutes", type=float, default=0.0,
                   help="billable minutes for an unanswered dial (0 on most per-connected-minute plans)")
    a.add_argument("--max-gardeners", type=int, default=6)
    a.add_argument("--want", type=int, default=2)
    a.add_argument("--fee-per-visit", type=int, default=30)
    a.add_argument("--visits", type=int, default=3, help="visits in a typical job (5-day trip, alternate days)")
    a.add_argument("--min-revenue", type=int, default=99, help="minimum we earn per booking (booking fee)")
    a.add_argument("--booking-rate", type=float, default=0.4, help="share of customers with an offer who pay")
    a.add_argument("--fixed-monthly", type=int, default=500, help="number rental etc. (INR/month, estimate)")
    p = a.parse_args()
    if p.runs:
        actuals(p.runs)
    else:
        table(p)


if __name__ == "__main__":
    main()
