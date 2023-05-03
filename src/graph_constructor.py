'''
This script constructs a graph of Uniswap pools which were collected from pool_collector.py.
'''

# third party imports
import networkx as nx
# import matplotlib.pyplot as plt

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
        elif 'totalValueLockedUSD' in pool:
            metric = pool['totalValueLockedUSD']
        elif 'liquidity' in pool:
            metric = pool['liquidity']
        # make the node SYMBOL1_SYMBOL2_ID
        G.add_node(
            pool['token0']['symbol'] + '_' + pool['token1']['symbol'] + '_' + pool['id'], id=pool['id'], 
            metric=metric,
            token0=pool['token0'],
            token1=pool['token1'],
            reserve0=pool['reserve0'],
            reserve1=pool['reserve1'],
            price_impact=0,
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
