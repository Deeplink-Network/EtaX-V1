'''
This script constructs a graph of Uniswap pools which were collected from pool_collector.py.
'''

# third party imports
import networkx as nx
import matplotlib.pyplot as plt

# standard library imports
import json

# create a graph where each pool is a node
def construct_pool_graph(pools: json) -> nx.classes.graph.Graph:
    # create a graph
    G = nx.DiGraph()
    # add a node for each pool
    for pool in pools:
        '''# if at least one of the pool's symbols are tokens A or B
        if pool['token0']['symbol'] == tokenA or pool['token0']['symbol'] == tokenB or pool['token1']['symbol'] == tokenA or pool['token1']['symbol'] == tokenB:'''
        # check if the pool has reserveUSD or liquidityUSD
        if 'reserveUSD' in pool:
            metric = pool['reserveUSD'] 
        elif 'liquidityUSD' in pool:
            metric = pool['liquidityUSD']
        # make the node SYMBOL1_SYMBOL2_ID
        G.add_node(
            pool['token0']['symbol'] + '_' + pool['token1']['symbol'] + '_' + pool['id'], id=pool['id'], 
            metric=metric,
            token0=pool['token0'],
            token1=pool['token1'],
            reserve0=pool['reserve0'],
            reserve1=pool['reserve1'],
            pool=pool)

    # connect the nodes if they share a token
    for node in list(G.nodes):
        for node2 in list(G.nodes):
            # check for common tokens
            if G.nodes[node]['token0']['id'] == G.nodes[node2]['token0']['id'] or G.nodes[node]['token0']['id'] == G.nodes[node2]['token1']['id'] or G.nodes[node]['token1']['id'] == G.nodes[node2]['token0']['id'] or G.nodes[node]['token1']['id'] == G.nodes[node2]['token1']['id']:
                # add an edge in both directions
                G.add_edge(node, node2)
                G.add_edge(node2, node)

    # remove nodes that can't form a path
    for node in list(G.nodes):
        if len(list(G.edges(node))) < 3:
            G.remove_node(node)

    # return the graph
    return G

def pool_graph_to_dict(G: nx.DiGraph()) -> dict:
    return nx.to_dict_of_lists(G)

# draw the graph in a circular layout
def draw_pool_graph(G: nx.DiGraph()) -> None:
    # labels are SYMBOLA SYMBOLB
    labels = {}
    for node in list(G.nodes):
        # get the node's pool
        pool = G.nodes[node]['pool']
        # get the node's token0 symbol
        token0 = pool['token0']['symbol']
        # get the node's token1 symbol
        token1 = pool['token1']['symbol']
        # add the label to the dictionary
        labels[node] = f'{token0}\n{token1}'

    # use the node's reserve as the node size
    sizes = []
    for node in list(G.nodes):
        # get the node's reserve
        reserve = G.nodes[node]['reserveUSD']
        # add the reserve to the list
        sizes.append(float(reserve))
        
    # normalize sizes
    sizes = [x/max(sizes)*10000+2000 for x in sizes]

    # draw the graph
    nx.draw_circular(G, with_labels=True, labels=labels, node_size=sizes, font_size=16, node_color='lightblue', edge_color='grey', arrows=False)
    # make the plot larger
    plt.rcParams['figure.figsize']=(25,25)
    # increase the font size
    plt.rcParams.update({'font.size': 26})
    # increase the res
    # plt.savefig('data/graph.png', dpi=200)
    plt.show()