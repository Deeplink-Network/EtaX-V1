'''
This module contains the main function for the smart order router, calling all the other relevant modules.
'''

# local imports
from pool_collector import get_latest_pool_data, collect_curve_pools, reformat_balancer_pools
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route
# third party imports
import logging
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V2, DODO, PANCAKESWAP_V3, MAX_ROUTES
from heapq import merge
import json
import time

MAX_ORDERS = 20

DEX_LIST = (
    #UNISWAP_V2,
    #UNISWAP_V3,
    #SUSHISWAP_V2,
    CURVE,
    #BALANCER_V2,
    #DODO,
    PANCAKESWAP_V3
)

DEX_METRIC_MAP = {
    UNISWAP_V2: 'reserveUSD',
    UNISWAP_V3: 'totalValueLockedUSD',
    SUSHISWAP_V2: 'liquidityUSD',
    CURVE: 'reserveUSD',
    BALANCER_V2: 'liquidity',
    DODO: 'volumeUSD',
    PANCAKESWAP_V3: 'totalValueLockedUSD'
}

BLACKLISTED_TOKENS = [
    '0xd233d1f6fd11640081abb8db125f722b5dc729dc'  # Dollar Protocol
]

pool_dict = {}
# pools = [None] * 200_000
pools = {
    exch: {
        'metric': DEX_METRIC_MAP[exch],
        'pools': [None] * 10_000
    } for exch in DEX_LIST
}


async def refresh_pools(protocol: str):
    # print('refreshing pools...')

    global pools
    global pool_dict
    
    if protocol == CURVE:
        new_curve_pools = await collect_curve_pools()
        for pool in new_curve_pools:
            pool_dict[pool['id']] = pool
            pools[protocol]['pools'].append(pool)
        print(f'{protocol} pool count: {len([pool for pool in pools[protocol]["pools"] if pool is not None])}')
        return
    # get the latest pool data
    new_pools = []
    metric_to_use = pools[protocol]['metric']
    last_pool_metric = None
    for i in range(0, 1):
        for skip in (0, 1000, 2000, 3000, 4000, 5000):
            logging.info(
                f'getting pools {i*6000 + skip} to {i*6000 + skip + 1000}...')
            new_pools = await get_latest_pool_data(protocol=protocol, skip=skip, max_metric=last_pool_metric)
            if new_pools:
                if protocol == BALANCER_V2:
                    new_balancer_pools = reformat_balancer_pools(new_pools)
                    for pool in new_balancer_pools:
                        pool_dict[pool['id']] = pool
                        pools[protocol]['pools'].append(pool)  # Add this line
                else:
                    for pool in new_pools:
                        pool_dict[pool['id']] = pool
                        pools[protocol]['pools'].append(pool)  # Add this line

                print("total pools collected:"+str(len(pool_dict)))
                last_pool = new_pools[-1]
                # print("last_pool:", last_pool)
                last_pool_metric = float(last_pool[metric_to_use])
                # print(f'last pool metric: {last_pool_metric} {metric_to_use}')
                print(f'{protocol} pool count: {len([pool for pool in pools[protocol]["pools"] if pool is not None])}')


# pool sorting helper function
def pool_key(pool):
    try:
        if pool is None:
            return 0
        metric_key = pools[pool['protocol']]['metric']
        return float(pool['reserveUSD']) if 'reserveUSD' in pool else float(pool[metric_key]) if pool else 0
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Pool causing error: {pool}")
        print(f"reserveUSD: {pool.get('reserveUSD', 'Not Found')}")
        print(f"Protocol: {pool.get('protocol', 'Not Found')}")
        print(f"Metric: {pools[pool['protocol']].get('metric', 'Not Found')}")
        return 0


# filter the pools for the query
def filter_pools(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, exchanges=None, X: int = 50) -> list:
    filtered_pools = []
    # Use 'reserveUSD' if available, or the default metric from the 'pools' dictionary
    # ideally we should probably decouple the metric for pagination and the metric for sorting
    full_pools = merge(*[pools[protocol]['pools'] for protocol in DEX_LIST], reverse=True, key=lambda x: float(x[pools[x['protocol']]['metric']]) if x else 0)
    #full_pools = merge(*[pools[protocol]['pools'] for protocol in DEX_LIST], reverse=True, key=pool_key)
    sell_count = 0
    buy_count = 0
    min_count = 1

    for pool in full_pools:
        if not pool or exchanges is not None and pool['protocol'] not in exchanges:
            continue
        if sell_count >= X and buy_count >= X:
            return filtered_pools
        if sell_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            sell_count += 1
            if sell_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
        if buy_ID in (pool['token0']['id'], pool['token1']['id']):
            # check if either token is blacklisted
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue
            buy_count += 1
            if buy_count < X and pool not in filtered_pools:
                filtered_pools.append(pool)
    if buy_count < min_count or sell_count < min_count:
        logging.warning('Insufficient pools cached, sleeping and retrying with full DEX list...')
        logging.warning(
            f'Final buy count: {buy_count}, final sell count: {sell_count}')
        return []

    return filtered_pools

async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str, exchanges, split=False) -> dict:
    result = {}
    # get the pools
    filt_pools = filter_pools(sell_symbol, sell_ID,
                              buy_symbol, buy_ID, exchanges=exchanges)
    if len(filt_pools) < 5:
        time.sleep(5)
        filter_pools(sell_symbol, sell_ID,
                              buy_symbol, buy_ID, exchanges=DEX_LIST)
    # print(json.dumps(filt_pools, indent=4))
    # construct the pool graph
    G = construct_pool_graph(filt_pools)
    # get the graph dict
    graph_dict = pool_graph_to_dict(G)
    # append the dict to the result
    result['pool_graph'] = graph_dict
    # find the shortest paths
    paths = find_shortest_paths(G, sell_symbol, buy_symbol)
    # validate the paths
    valid_paths = validate_all_paths(G, paths, sell_ID, buy_ID)
    # create the path graph
    path_graph = create_path_graph(valid_paths)
    # get the path graph dict
    path_graph_dict = path_graph_to_dict(path_graph)
    # append the dict to the result
    result['path_graph'] = path_graph_dict
    # calculate the routes (traverse the paths and calculate price impact at each swap)
    routes = calculate_routes(
        G, valid_paths, sell_amount, sell_symbol, buy_symbol)
    if split:
        final_route = get_final_route(G, routes, sell_amount, sell_symbol)
        result['routes'] = final_route
    else:
        result['routes'] = routes[:MAX_ROUTES]
    return result
