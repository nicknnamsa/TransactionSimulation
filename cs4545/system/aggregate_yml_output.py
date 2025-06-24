#!/usr/bin/env python3
"""
aggregate_yml_output.py

Collect *.yml stats dumped by every container into one CSV row.
Usage:
    python aggregate_yml_output.py          # defaults
    python aggregate_yml_output.py -i run1/output -o aggregated/run1.csv
"""

from pathlib import Path
import argparse, csv, yaml, statistics, sys

DEFAULT_IN  = Path("output")
DEFAULT_OUT = Path("aggregated_output/transaction.csv")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input",  type=Path, default=DEFAULT_IN,
                   help="directory containing per‑node *.yml files")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT,
                   help="CSV file to append aggregated row to")
    return p.parse_args()

def main():
    args = parse_args()
    yml_files = sorted(args.input.glob("*.yml"))
    if not yml_files:
        sys.exit(f"No .yml files found in {args.input}")

    # ── gather ──────────────────────────────────────────────────────
    all_metrics = []
    for f in yml_files:
        with f.open() as fh:
            all_metrics.append(yaml.safe_load(fh))

    n_nodes = len(all_metrics)

    # Extract basic numeric columns that every YAML has
    latencies   = [m.get("latency", 0)            for m in all_metrics]
    tx_counts   = [m.get("number_transaction", 0) for m in all_metrics]
    bytes_sent  = [m.get("bytes_sent", 0)         for m in all_metrics]

    avg_lat = sum(latencies) / n_nodes
    med_lat = statistics.median(latencies)
    tot_tx  = sum(tx_counts)
    tot_b   = sum(bytes_sent)

    # ── make sure output folder exists ──────────────────────────────
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # ── write / append CSV ──────────────────────────────────────────
    header = [
        "no_nodes", "avg_latency", "median_latency",
        "total_transactions", "total_bytes"
    ]
    row = [n_nodes, avg_lat, med_lat, tot_tx, tot_b]

    # Add any extra keys automatically
    extras = sorted({k for m in all_metrics for k in m.keys()}
                    - {"latency", "number_transaction", "bytes_sent"})
    for k in extras:
        header.append(f"sum_{k}")
        row.append(sum(m.get(k, 0) for m in all_metrics))

    # Append or create
    new_file = not args.output.exists()
    with args.output.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(header)
        w.writerow(row)

    # ── console summary ─────────────────────────────────────────────
    print(f"Aggregated {n_nodes} nodes → {args.output}")
    print(f"  avg latency  = {avg_lat:.3f} s")
    print(f"  median       = {med_lat:.3f} s")
    print(f"  total tx     = {tot_tx}")
    print(f"  total bytes  = {tot_b}")

if __name__ == "__main__":
    main()
