'''
This module contains the main function for the smart order router, calling all the other relevant modules.
'''

# local imports
from pool_collector import get_latest_pool_data, get_pool_permutations
import asyncio
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes
# third party imports
import networkx as nx
import json
import sys

pools = []

async def refresh_pools():
    global pools
    # get the latest pool data
    new_pools = []
    for skip in (0, 1000, 2000, 3000, 4000, 5000):
        new_pools += await get_latest_pool_data(skip=skip)
    pools = new_pools
        # await asyncio.sleep(5)

def filter_pools(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, X: int = 50) -> list:
    filtered_pools = []
    sell_count = 0
    buy_count = 0
    for pool in pools:
        if sell_symbol in (pool['token0']['symbol'], pool['token1']):
            sell_count += 1
            if sell_count < X:
                filtered_pools.append(pool)
                continue
        if buy_symbol in (pool['token0']['symbol'], pool['token1']):
            buy_count += 1
            if buy_count < X:
                filtered_pools.append(pool)
                continue
    if buy_count == 0 or sell_count == 0:
        return []
    return filtered_pools

async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str) -> dict:
    result = {}
    # get the pools
    # pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    # construct the pool graph
    filt_pools = filter_pools(sell_symbol, sell_ID, buy_symbol, buy_ID)
    if len(filt_pools) < 60:
        filt_pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    G = construct_pool_graph(filt_pools)
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