'''
This file contains the functions that find the shortest paths between two symbols.
'''

# third party imports
import networkx as nx
import matplotlib.pyplot as plt

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
            paths.append(list(nx.shortest_path(G, sell_node, buy_node, method='bellman-ford')))
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

'''
check path validity using get_partner_symbol function
enter the first node, swap sell_symbol for the node's other token
enter the next node, swap the previous node's other token for the node's other token and so on
if the final node outputs buy_symbol, the path is valid
'''
def check_path_validity(path: list, sell_symbol: str, buy_symbol: str) -> bool:
    for node in path:
        # for the first node
        if node == path[0]:
            output_token = get_partner_symbol(node, sell_symbol)
        # for the other nodes
        else:
            if output_token not in node:
                return False 
            output_token = get_partner_symbol(node, output_token)
        # for the last node
        if node == path[-1]:
            if output_token != buy_symbol:
                return False
                
    return True

# check the validity of all paths
def validate_all_paths(G: nx.classes.digraph.Graph, paths: list, sell_symbol: str, buy_symbol: str) -> list:
    valid_paths = []
    for path in paths:
        if check_path_validity(path, sell_symbol, buy_symbol):
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