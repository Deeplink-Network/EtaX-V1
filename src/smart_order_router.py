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
import logging

BLACKLISTED_TOKENS = [
    '0xd233d1f6fd11640081abb8db125f722b5dc729dc' # Dollar Protocol
    ]

pools = [None] * 200_000

async def refresh_pools():
    global pools
    # get the latest pool data
    new_pools = []
    last_pool_reserves = None
    for i in range(0, 30):
        for skip in (0, 1000, 2000, 3000, 4000, 5000):
            logging.info(f'getting pools {i*6000 + skip} to {i*6000 + skip + 1000}...')
            new_pools = await get_latest_pool_data(skip=skip, max_reserves=last_pool_reserves)
            if new_pools:
                pools[i*6000 + skip: i*6000 + skip + len(new_pools)] = new_pools
        last_pool = new_pools[-1]
        last_pool_reserves = float(last_pool['reserveUSD'])
    #pools = new_pools
    # await asyncio.sleep(5)

def filter_pools(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, X: int = 50) -> list:
    filtered_pools = []
    sell_count = 0
    buy_count = 0
    min_count = 10
    for i, pool in enumerate(pools):
        if not pool:
            logging.info("Didn't reach the max number of pools for the graph")
            return filtered_pools
        if sell_count >= X and buy_count >= X:
            return filtered_pools
        if sell_symbol in (pool['token0']['symbol'], pool['token1']['symbol']):
            sell_count += 1
            if sell_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
        if buy_symbol in (pool['token0']['symbol'], pool['token1']['symbol']):
            buy_count += 1
            if buy_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
    if buy_count < min_count or sell_count < min_count:
        logging.warning('Insufficient pools cached, using old method')
        logging.warning(f'Final buy count: {buy_count}, final sell count: {sell_count}')
        return []
    return filtered_pools

# rewrite filter pools to use id instead of symbol
def filter_pools_by_id(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, X: int = 50) -> list:
    filtered_pools = []
    sell_count = 0
    buy_count = 0
    min_count = 10
    for i, pool in enumerate(pools):
        if not pool:
            print(i)
            return filtered_pools
        if sell_count >= X and buy_count >= X:
            return filtered_pools
        if sell_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            sell_count += 1
            if sell_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
                continue
        if buy_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            buy_count += 1
            if buy_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
    if buy_count < min_count or sell_count < min_count:
        logging.warning('Insufficient pools cached, using old method')
        logging.warning(f'Final buy count: {buy_count}, final sell count: {sell_count}')
        return []
    return filtered_pools

# rewrite filter pools to use id instead of symbol
def filter_pools_by_id(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, X: int = 50) -> list:
    filtered_pools = []
    sell_count = 0
    buy_count = 0
    min_count = 10
    for i, pool in enumerate(pools):
        if not pool:
            print(i)
            return filtered_pools
        if sell_count >= X and buy_count >= X:
            return filtered_pools
        if sell_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            sell_count += 1
            if sell_count < X:
                filtered_pools.append(pool)
                continue
        if buy_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            buy_count += 1
            if buy_count < X:
                filtered_pools.append(pool)
                continue
    if buy_count < min_count or sell_count < min_count:
        return []
    return filtered_pools

async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str) -> dict:
    result = {}
    # get the pools
    # pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    # construct the pool graph
    filt_pools = filter_pools_by_id(sell_symbol, sell_ID, buy_symbol, buy_ID)
    if len(filt_pools) < 25:
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