import os
import click
import networkx as nx
import matplotlib.pyplot as plt
import yaml
import random


@click.group()
def cli():
    pass


def generate_graph(num_nodes, connectivity, full_conn=False):
    if not full_conn:
        finished = False
        # IMPORTANT: adjust p value to smaller, if you want sparser graph to begin with
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


def save_graph_to_yaml(graph, num_nodes, connectivity, output_folder, full_conn=False):
    adjacency_dict = {node: list(graph.neighbors(node)) for node in graph.nodes()}
    if not full_conn:
        filename = f"{connectivity}connected_{num_nodes}graph.yaml"
    else:
        filename = f"fully_connected_{num_nodes}graph.yaml"
    filepath = os.path.join(output_folder, filename)

    with open(filepath, 'w') as yaml_file:
        yaml.dump(adjacency_dict, yaml_file, default_flow_style=False)

    print(f"Graph saved to: {filepath}")


@cli.command('gen_graph')
@click.argument('num_nodes', type=int)
@click.argument('connectivity', type=int)
@click.argument('draw', type=bool, default=False)
@click.argument('full_conn', type=bool, default=False)
def gen_graph(num_nodes, connectivity, draw, full_conn):
    graph = generate_graph(num_nodes, connectivity, full_conn)
    if not full_conn:
        print(f"Graph is {nx.node_connectivity(graph)}-connected.")
    else:
        print(f"Graph is fully connected.")
    output_path = "topologies"
    save_graph_to_yaml(graph, num_nodes, connectivity, output_path, full_conn)
    if draw:
        nx.draw(graph, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500)
        plt.show()


if __name__ == '__main__':
    cli()
