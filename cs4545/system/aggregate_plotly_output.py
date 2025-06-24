from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DEFAULT_IN = Path("output")
DEFAULT_CSV_OUT = Path("aggregated_output/transaction.csv")
DEFAULT_GRAPH_DIR = Path("aggregated_output/plots")

def parse_args():
    p = argparse.ArgumentParser(description="Aggregate node .yml stats and plot with Plotly")
    p.add_argument("-i", "--input", type=Path, default=DEFAULT_IN,
                   help="directory containing per‑node *.yml files (default: output/)")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_CSV_OUT,
                   help="CSV file to append aggregated row to (default: aggregated_output/transaction.csv)")
    p.add_argument("-g", "--graphs", type=Path, default=DEFAULT_GRAPH_DIR,
                   help="directory to write Plotly HTML+PNG files (default: aggregated_output/plots/)")
    return p.parse_args()

def load_yaml_stats(files: List[Path]) -> List[Dict[str, Any]]:
    metrics = []
    for f in files:
        with f.open() as fh:
            d = yaml.safe_load(fh)
            d["_node_id"] = _node_id_from_fname(f)
            metrics.append(d)
    return metrics


def _node_id_from_fname(p: Path) -> int:
    digits = ''.join(c for c in p.stem if c.isdigit())
    return int(digits) if digits else -1

def write_csv_row(all_metrics: List[Dict[str, Any]], csv_out: Path):
    n_nodes = len(all_metrics)
    latencies = [m.get("latency", 0) for m in all_metrics]
    tx_counts = [m.get("number_transaction", 0) for m in all_metrics]
    bytes_sent = [m.get("bytes_sent", 0) for m in all_metrics]

    avg_lat = sum(latencies) / n_nodes if n_nodes else 0
    med_lat = statistics.median(latencies) if latencies else 0
    tot_tx = sum(tx_counts)
    tot_b = sum(bytes_sent)

    header = [
        "no_nodes", "avg_latency", "median_latency",
        "total_transactions", "total_bytes",
    ]
    row = [n_nodes, avg_lat, med_lat, tot_tx, tot_b]

    extras = sorted({k for m in all_metrics for k in m.keys()} - {
        "latency", "number_transaction", "bytes_sent", "_node_id"})
    for k in extras:
        header.append(f"sum_{k}")
        row.append(sum(m.get(k, 0) for m in all_metrics))

    csv_out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not csv_out.exists()
    with csv_out.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(header)
        w.writerow(row)
    print(f"CSV row appended → {csv_out}")

def make_plots(df: pd.DataFrame, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)

    fig1 = px.bar(df, x="_node_id", y="number_transaction",
                  labels={"_node_id": "Node", "number_transaction": "Transactions"},
                  title="Transactions processed per node")
    _save(fig1, outdir / "transactions_per_node")

    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(x=df["latency"], nbinsx=15, name="Latency"))
    fig2.add_trace(go.Violin(y=df["latency"], name="", box_visible=True, meanline_visible=True, showlegend=False))
    fig2.update_layout(title="Latency distribution across nodes",
                       xaxis_title="Latency (s)", yaxis_title="Count")
    _save(fig2, outdir / "latency_distribution")

    fig3 = px.pie(df, names="_node_id", values="bytes_sent", title="Network load share (bytes sent)")
    _save(fig3, outdir / "bytes_per_node")

    if {"bloom_items", "utxo_pool_size", "tx_seen"}.issubset(df.columns):
        fig4 = px.scatter(df, x="bloom_items", y="utxo_pool_size", size="tx_seen",
                          hover_name="_node_id", title="Bloom occupancy vs. UTXO pool size",
                          labels={"bloom_items": "Bloom items", "utxo_pool_size": "UTXO pool size"})
        _save(fig4, outdir / "bloom_vs_utxo")

    fig5 = px.scatter(df, x="latency", y="number_transaction", text="_node_id",
                      labels={"latency": "Latency (s)", "number_transaction": "Transactions"},
                      title="Latency vs. Transactions processed")
    fig5.update_traces(textposition="top center")
    _save(fig5, outdir / "latency_vs_tx")

    try:
        rel = outdir.relative_to(Path.cwd())
    except ValueError:
        rel = outdir
    print(f"✓ Plots saved in {rel}")


def _save(fig, basepath: Path):
    html_path = basepath.with_suffix(".html")
    png_path = basepath.with_suffix(".png")
    fig.write_html(html_path)
    try:
        fig.write_image(png_path, scale=2)
    except ValueError as e:
        print(f"[warn] PNG export failed ({e}); HTML only at {html_path}")


def main():
    args = parse_args()

    yml_files = sorted(args.input.glob("*.yml"))
    if not yml_files:
        sys.exit(f"No .yml files found in {args.input}")

    metrics = load_yaml_stats(yml_files)
    df = pd.DataFrame(metrics)

    write_csv_row(metrics, args.output)
    make_plots(df, args.graphs)

    print("────────────────────────────────────────────────────────")
    print(f"Aggregated {len(df)} nodes → {args.output}")
    print(df[["_node_id", "number_transaction", "latency", "bytes_sent"]]
          .sort_values("_node_id")
          .to_string(index=False))


if __name__ == "__main__":
    main()
