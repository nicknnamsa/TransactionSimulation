#!/usr/bin/env python3
"""
CLI identical to the original `gen_graph` script – *except* that when you pass
`draw=True` it renders an **interactive Plotly** visual rather than a static
Matplotlib window.

Example (same flags):
    $ python generate_graph_plotly.py gen_graph 30 2 True

Outputs:
    • YAML adjacency list in `topologies/`
    • `topologies/<…>.html` (and `.png` if kaleido available) with the graph.
"""
import os
import random
from pathlib import Path

import click
import networkx as nx
import plotly.graph_objects as go
import yaml

# ----------------------------------------------------------------------------
@click.group()
def cli():
    pass

# ----------------------------------------------------------------------------
# Graph generation – same logic as before
# ----------------------------------------------------------------------------

def generate_graph(num_nodes, connectivity, full_conn=False):
    if not full_conn:
        finished = False
        graph = nx.gnp_random_graph(num_nodes, p=0.16)
        while not finished:
            if nx.node_connectivity(graph) < connectivity:
                graph = nx.gnp_random_graph(num_nodes, p=0.16)
            else:
                finished = True
        while nx.node_connectivity(graph) > connectivity:
            u, v = random.choice(list(graph.edges()))
            graph.remove_edge(u, v)
    else:
        graph = nx.complete_graph(num_nodes)
    return graph

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def save_graph_to_yaml(graph, num_nodes, connectivity, output_folder, full_conn=False):
    adjacency_dict = {node: list(graph.neighbors(node)) for node in graph.nodes()}
    if not full_conn:
        filename = f"{connectivity}connected_{num_nodes}graph.yaml"
    else:
        filename = f"fully_connected_{num_nodes}graph.yaml"
    filepath = os.path.join(output_folder, filename)

    os.makedirs(output_folder, exist_ok=True)
    with open(filepath, "w") as yaml_file:
        yaml.dump(adjacency_dict, yaml_file, default_flow_style=False)

    print(f"✓ YAML saved to {filepath}")
    return Path(filepath)


def plot_graph_plotly(graph: nx.Graph, html_path: Path):
    pos = nx.spring_layout(graph, seed=42)

    # Edges
    edge_x, edge_y = [], []
    for u, v in graph.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none",
    )

    # Nodes
    node_x, node_y = [], []
    for n in graph.nodes():
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[str(n) for n in graph.nodes()],
        textposition="middle center",
        marker=dict(size=12, color="#1f77b4", line=dict(width=1, color="white")),
        hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(title="Generated topology",
                                     showlegend=False,
                                     margin=dict(l=20, r=20, t=40, b=20),
                                     xaxis=dict(showgrid=False, zeroline=False, visible=False),
                                     yaxis=dict(showgrid=False, zeroline=False, visible=False)))

    # Save alongside YAML
    fig.write_html(str(html_path.with_suffix(".html")))
    try:
        fig.write_image(str(html_path.with_suffix(".png")), scale=2)
    except ValueError:
        pass  # kaleido not installed; HTML still saved
    print(f"✓ Plotly visual saved ➟ {html_path.with_suffix('.html')}")

# ----------------------------------------------------------------------------
# CLI command – identical signature
# ----------------------------------------------------------------------------

@cli.command("gen_graph")
@click.argument("num_nodes", type=int)
@click.argument("connectivity", type=int)
@click.argument("draw", type=bool, default=False)
@click.argument("full_conn", type=bool, default=False)

def gen_graph(num_nodes, connectivity, draw, full_conn):
    graph = generate_graph(num_nodes, connectivity, full_conn)

    if not full_conn:
        print(f"Graph is {nx.node_connectivity(graph)}‑connected.")
    else:
        print("Graph is fully connected.")

    output_path = "topologies"
    yaml_path = save_graph_to_yaml(graph, num_nodes, connectivity, output_path, full_conn)

    if draw:
        plot_graph_plotly(graph, yaml_path)
    else:
        print("(visualisation skipped)")

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    cli()
