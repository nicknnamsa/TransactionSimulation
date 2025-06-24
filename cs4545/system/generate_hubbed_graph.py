from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Dict, List

import click
import networkx as nx
import plotly.graph_objects as go
import yaml

def make_cluster(size: int, p_intra: float) -> nx.Graph:

    return nx.gnp_random_graph(size, p_intra)


def relabel_cluster(g: nx.Graph, offset: int) -> nx.Graph:
    mapping = {old: old + offset for old in g.nodes()}
    return nx.relabel_nodes(g, mapping)


def add_bridge_edges(G: nx.Graph, cluster_nodes: List[int], other_nodes: List[int], n: int):

    for _ in range(n):
        u = random.choice(cluster_nodes)
        v = random.choice(other_nodes)
        G.add_edge(u, v)


def build_hubbed_graph(k: int, cluster_size: int, p_intra: float = 0.6, bridge_edges: int = 1) -> nx.Graph:

    clusters: List[nx.Graph] = []
    offset = 0
    for _ in range(k):
        g = make_cluster(cluster_size, p_intra)
        g = relabel_cluster(g, offset)
        clusters.append(g)
        offset += cluster_size

    G = nx.Graph()
    for g in clusters:
        G = nx.compose(G, g)

    for i in range(k):
        for j in range(i + 1, k):
            add_bridge_edges(G,
                             list(clusters[i].nodes()),
                             list(clusters[j].nodes()),
                             bridge_edges)
    return G


def save_yaml(G: nx.Graph, path: Path):
    adj: Dict[int, List[int]] = {n: sorted(list(G.neighbors(n))) for n in G.nodes()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        yaml.dump(adj, fh)
    print(f"✓ YAML saved ➟ {path}")


def plot_plotly(G: nx.Graph, path: Path):
    pos = nx.spring_layout(G, seed=42)

    edge_x = []
    edge_y = []
    for u, v in G.edges():
        edge_x.extend([pos[u][0], pos[v][0], None])
        edge_y.extend([pos[u][1], pos[v][1], None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#888"), hoverinfo="none")

    k = len(set(n // (len(G) // max(1, len(G))) for n in G.nodes()))
    cluster_size = len(G) // k
    node_x = []
    node_y = []
    node_color = []
    for n in G.nodes():
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])
        node_color.append(n // cluster_size)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers", marker=dict(size=12, color=node_color, colorscale="Viridis", line_width=1),
        text=[str(n) for n in G.nodes()], hoverinfo="text")

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(title="Hubbed topology",
                                     showlegend=False,
                                     margin=dict(l=20, r=20, t=40, b=20),
                                     xaxis=dict(showgrid=False, zeroline=False, visible=False),
                                     yaxis=dict(showgrid=False, zeroline=False, visible=False)))

    path.parent.mkdir(parents=True, exist_ok=True)

    fig.write_html(path.with_suffix(".html"))
    try:
        fig.write_image(path.with_suffix(".png"), scale=2)
    except ValueError:
        pass
    print(f"✓ Plotly graph saved ➟ {path.with_suffix('.html')}")


@click.command("hub_graph")
@click.option("--clusters", "k", type=int, default=4, help="number of clusters (neighbourhoods)")
@click.option("--size", "cluster_size", type=int, default=8, help="nodes per cluster")
@click.option("--p_intra", type=float, default=0.6, help="intra‑cluster edge probability")
@click.option("--bridges", "bridge_edges", type=int, default=1, help="bridge edges between every pair of clusters")
@click.option("--draw/--no-draw", default=True, help="output Plotly visualisation")
def main(k: int, cluster_size: int, p_intra: float, bridge_edges: int, draw: bool):
    """Generate a hubbed graph and save YAML (always) + Plotly (optional)."""

    G = build_hubbed_graph(k, cluster_size, p_intra, bridge_edges)
    n = len(G)

    topo_dir = Path("topologies")
    yaml_path = topo_dir / f"hubbed_{k}clusters_{n}nodes.yaml"
    save_yaml(G, yaml_path)

    if draw:
        plot_path = topo_dir / f"hubbed_{k}clusters_{n}nodes"
        plot_plotly(G, plot_path)
    else:
        print("(visualisation skipped)\n")


if __name__ == "__main__":
    main()
