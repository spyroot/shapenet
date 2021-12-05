import io
import re

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def fmtl_print(left, *argv):
    if len(argv) == 1:
        print(f"{str(left) + ':' :<32} {argv[0]}")
    else:
        print(f"{str(left) + ':' :<32} {argv}")


def fmt_print(left, *argv):
    if len(argv) == 1:
        print(f"{str(left) + ':' :<25} {argv[0]}")
    else:
        print(f"{str(left) + ':' :<25} {argv}")


def perturb(graph_list, p_del, p_add=None):
    """ Perturb the list of graphs by adding/removing edges.
    Args:
        p_add: probability of adding edges. If None, estimate it according to graph density,
                such that the expected number of added edges is equal to that of deleted edges.
        p_del: probability of removing edges
    Returns:
        A list of graphs that are perturbed from the original graphs
    """
    perturbed_graph_list = []
    for G_original in graph_list:
        G = G_original.copy()
        trials = np.random.binomial(1, p_del, size=G.number_of_edges())
        edges = list(G.edges())
        i = 0
        for (u, v) in edges:
            if trials[i] == 1:
                G.remove_edge(u, v)
            i += 1
        if p_add is None:
            num_nodes = G.number_of_nodes()
            p_add_est = np.sum(trials) / (num_nodes * (num_nodes - 1) / 2 -
                                          G.number_of_edges())
        else:
            p_add_est = p_add

        nodes = list(G.nodes())
        tmp = 0
        for i in range(len(nodes)):
            u = nodes[i]
            trials = np.random.binomial(1, p_add_est, size=G.number_of_nodes())
            j = 0
            for j in range(i + 1, len(nodes)):
                v = nodes[j]
                if trials[j] == 1:
                    tmp += 1
                    G.add_edge(u, v)
                j += 1

        perturbed_graph_list.append(G)
    return perturbed_graph_list


def perturb_new(graph_list, p):
    """ Perturb the list of graphs by adding/removing edges.
    Args:
        p_add: probability of adding edges. If None, estimate it according to graph density,
               such that the expected number of added edges is equal to that of deleted edges.
        p_del: probability of removing edges

    Returns:
        A list of graphs that are perturbed from the original graphs
    """
    perturbed_graph_list = []
    for G_original in graph_list:
        G = G_original.copy()
        edge_remove_count = 0
        for (u, v) in list(G.edges()):
            if np.random.rand() < p:
                G.remove_edge(u, v)
                edge_remove_count += 1
        # randomly add the edges back
        for i in range(edge_remove_count):
            while True:
                u = np.random.randint(0, G.number_of_nodes())
                v = np.random.randint(0, G.number_of_nodes())
                if (not G.has_edge(u, v)) and (u != v):
                    break
            G.add_edge(u, v)
        perturbed_graph_list.append(G)
    return perturbed_graph_list


def image_buffered(graph, layout='spring', k=1, node_size=55,
                   alpha=1, width=1.3):
    plt.switch_backend('agg')
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    plt.axis("off")

    if layout == 'spring':
        pos = nx.spring_layout(graph, k=k / np.sqrt(graph.number_of_nodes()), iterations=100)
    elif layout == 'spectral':
        pos = nx.spectral_layout(graph)

    # node_size default 60, edge_width default 1.5
    # nx.draw_networkx_nodes(graph, pos, node_size=node_size, node_color='#336699', alpha=1, linewidths=0)
    # nx.draw_networkx_edges(graph, pos, alpha=alpha, width=width)

    fig, ax = plt.subplots()
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=node_size, node_color='#336699', alpha=1, linewidths=0)
    nx.draw_networkx_edges(graph, pos, ax=ax, alpha=alpha, width=width)

    with io.BytesIO() as buff:
        fig.savefig(buff, format='rgba')
        buff.seek(0)
        data = np.frombuffer(buff.getvalue(), dtype=np.uint8)

    fig.show()
    print(data.shape)
    w, h = fig.canvas.get_width_height()
    im = data.reshape((int(h), int(w), -1))
    print(im.shape)

    [b, g, r] = np.dsplit(im, im.shape[-1])

    # np_img = np.squeeze(im, axis=2)  # axis=2 is channel dimension
    print(r.shape)
    # m[:, :, 1]
    return r


def images_buffer_generator(graphs):
    for g in graphs:
        img = image_buffered(g)
        yield img


def get_graph(adj):
    """
    get a graph from zero-padded adj
    :param adj:
    :return:
    """
    # remove all zeros rows and columns
    adj = adj[~np.all(adj == 0, axis=1)]
    adj = adj[:, ~np.all(adj == 0, axis=0)]
    adj = np.asmatrix(adj)
    return nx.from_numpy_matrix(adj)


# pick the first connected component
def pick_connected_component(G):
    node_list = nx.node_connected_component(G, 0)
    return G.subgraph(node_list)


def pick_connected_component_new(G, low=1):
    """
    TODO
    """
    adj_list = G.adjacency_list()
    for id, adj in enumerate(adj_list):
        id_min = min(adj)
        if id_min > id >= low:
            break

    # only include node prior than node "id"
    node_list = list(range(id))
    G = G.subgraph(node_list)
    G = max(nx.connected_component_subgraphs(G), key=len)
    return G


# load a list of graphs
def load_generated_graphs(graph_list):
    """

    """
    for gid in range(len(graph_list)):
        loop_edges = list(nx.selfloop_edges(graph_list[gid]))
        if len(loop_edges) > 0:
            graph_list[gid].remove_edges_from(loop_edges)
        else:
            graph_list[gid] = pick_connected_component_new(graph_list[gid])
    return graph_list


# load a list of graphs
def load_graph_prediction(graph_list, is_real=True):
    """

    """
    for i in range(len(graph_list)):
        loop_edges = list(nx.selfloop_edges(graph_list[i]))
        if len(loop_edges) > 0:
            graph_list[i].remove_edges_from(loop_edges)
        if is_real:
            subgraph = (graph_list[i].subgraph(c) for c in nx.connected_components(graph_list[i]))
            graph_list[i] = max(subgraph, key=len)
            graph_list[i] = nx.convert_node_labels_to_integers(graph_list[i])
        else:
            graph_list[i] = pick_connected_component_new(graph_list[i])
    return graph_list


def export_graphs_to_txt(g_list, output_filename_prefix):
    i = 0
    for G in g_list:
        f = open(output_filename_prefix + '_' + str(i) + '.txt', 'w+')
        for (u, v) in G.edges():
            idx_u = G.nodes().index(u)
            idx_v = G.nodes().index(v)
            f.write(str(idx_u) + '\t' + str(idx_v) + '\n')
        i += 1


def snap_txt_output_to_nx(in_fname):
    G = nx.Graph()
    with open(in_fname, 'r') as f:
        for line in f:
            if not line[0] == '#':
                splitted = re.split('[ \t]', line)

                # self loop might be generated, but should be removed
                u = int(splitted[0])
                v = int(splitted[1])
                if not u == v:
                    G.add_edge(int(u), int(v))
    return G
