'''
This module contains the main function for the smart order router, calling all the other relevant modules.
'''

# local imports
from pool_collector import get_pool_permutations
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes
# third party imports
import networkx as nx
import json

async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str) -> dict:
    result = {}
    # get the pools
    pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    # construct the pool graph
    G = construct_pool_graph(pools)
    # get the graph dict
    graph_dict = pool_graph_to_dict(G)
    # append the dict to the result
    result['pool_graph'] = graph_dict
    # find the shortest paths
    paths = find_shortest_paths(G, sell_symbol, buy_symbol)
    # validate the paths
    valid_paths = validate_all_paths(G, paths, sell_symbol, buy_symbol)
    # create the path graph
    path_graph = create_path_graph(valid_paths)
    # get the path graph dict
    path_graph_dict = path_graph_to_dict(path_graph)
    # append the dict to the result
    result['path_graph'] = path_graph_dict
    # calculate the routes (traverse the paths and calculate price impact at each swap)
    routes = calculate_routes(G, valid_paths, sell_amount, sell_symbol, buy_symbol)
    # append the routes to the result
    result['routes'] = routes
    '''# save routes to file
    with open('routes.json', 'w') as f:
        json.dump(routes, f)'''
    return result