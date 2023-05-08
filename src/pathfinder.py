'''
This file contains the functions that find the shortest paths between two symbols.
'''

# third party imports
import networkx as nx
# import matplotlib.pyplot as plt

# get the shortest paths from sell_symbol to buy_symbol using bellman-ford
def find_shortest_paths(G: nx.classes.digraph.DiGraph, sell_symbol: str, buy_symbol: str) -> list:
    # get all nodes that contain the sell symbol
    sell_nodes = [node for node in list(G.nodes) if sell_symbol in node]
    # get all nodes that contain the buy symbol
    buy_nodes = [node for node in list(G.nodes) if buy_symbol in node]
    # get all paths
    paths = []
    # for each sell node
    for sell_node in sell_nodes:
        # for each buy node
        for buy_node in buy_nodes:
            # get the shortest path from the sell node to the buy node
            try:
                paths.append(list(nx.shortest_path(G, sell_node, buy_node)))
            except:
                pass
    # sort the paths by length
    paths.sort(key=len)
    # return the paths
    return paths

def get_partner_symbol(node: str, current_symbol: str) -> str:
    # get the tokens in the node
    tokens = node.split('_')
    # if the first token is not the current symbol, return it
    if tokens[0] != current_symbol:
        return tokens[0]
    # else return the second token
    return tokens[1]

def get_partner_id(node: str, current_id: int, G: nx.classes.digraph.Graph) -> int:
    # get the IDs in the node
    node_data = G.nodes[node]
    ids = [node_data['token0']['id'], node_data['token1']['id']]
    # find the index of the current ID
    try:
        current_index = ids.index(current_id)
    except:
        return False # bit of a bandaid fix to the unusual token ticker problem, should probably rework the graph construction
    # return the ID at the other index
    return ids[(current_index + 1) % len(ids)]

def check_path_validity(G: nx.classes.digraph.Graph, path: list, sell_id: int, buy_id: int) -> bool:
    for node in path:
        node_data = G.nodes[node]
        # get the IDs in the node
        ids = [node_data[f"token{i}"]['id'] for i in range(2)]
        # for the first node
        if node == path[0]:
            output_id = get_partner_id(node, sell_id, G)
            if output_id == False:
                return False
        # for the other nodes
        else:
            # check if output_id is exactly one of the IDs in the node
            if output_id not in ids:
                return False 
            output_id = get_partner_id(node, output_id, G)
        # for the last node
        if node == path[-1]:
            if output_id != buy_id:
                return False
                
    return True

# check the validity of all paths
def validate_all_paths(G: nx.classes.digraph.Graph, paths: list, sell_id: int, buy_id: int) -> list:
    valid_paths = []
    for path in paths:
        if check_path_validity(G, path, sell_id, buy_id):
            valid_paths.append(path)

    return valid_paths

# run path validation over all paths
def create_path_graph(paths: list) -> nx.classes.graph.Graph:
    # make a multipartite graph out of these routes using their paths
    G = nx.Graph()
    # add the first nodes in the path to layer 0, the second nodes in the path to layer 1, etc.
    for path in paths:
        # add each node in the path
        for i in range(len(path)):
            G.add_node(path[i], layer=i)
            # make the node's symbol and id display as new lines
            G.nodes[path[i]]['symbol'] = path[i].split('_')[0] + '' + path[i].split('_')[1]
            G.nodes[path[i]]['id'] = path[i].split('_')[0] + '' + path[i].split('_')[1]

    # add the edges between the nodes
    for path in paths:
        for i in range(len(path)-1):
            G.add_edge(path[i], path[i+1])

    return G

# create a dictionary of the path graph
def path_graph_to_dict(G: nx.classes.graph.Graph) -> dict:
    return nx.to_dict_of_lists(G)

'''
# draw the paths as a multipartite graph    
def draw_path_graph(G: nx.classes.graph.Graph) -> None:
    # get the positions of the nodes
    pos = nx.multipartite_layout(G, subset_key="layer")
    # make the labels for the nodes
    labels = {}
    for node in G.nodes():
        labels[node] = G.nodes[node]['symbol']
    # draw the graph
    nx.draw(G, pos=pos, with_labels=True, labels=labels, node_size=1000, font_size=24)
    # show the graph
    plt.show()
'''