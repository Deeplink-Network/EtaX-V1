'''
This module contains the main function for the smart order router, calling all the other relevant modules.
'''

# local imports
from pool_collector import get_latest_pool_data, get_pool_permutations
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route
# third party imports
import logging
from heapq import merge

MAX_ORDERS = 20

DEX_LIST = (
    'Uniswap_V2',
    'Sushiswap_V2'
)

BLACKLISTED_TOKENS = [
    '0xd233d1f6fd11640081abb8db125f722b5dc729dc'  # Dollar Protocol
]

pool_dict = {}
# pools = [None] * 200_000
pools = {
    exch: {
        'metric': 'reserveUSD' if exch == 'Uniswap_V2' else 'liquidityUSD',
        'pools': [None] * 10_000
    } for exch in DEX_LIST
}
sushicount = 0
unicount = 0


async def refresh_pools(protocol: str):
    print('refreshing pools...')

    global sushicount
    global unicount

    global pools
    global pool_dict
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
                pools[protocol]['pools'][i*6000 + skip: i *
                                         6000 + skip + len(new_pools)] = new_pools
                print(len(pool_dict))
                last_pool = new_pools[-1]
                last_pool_metric = float(last_pool[metric_to_use])
                print(f'last pool metric: {last_pool_metric} {metric_to_use}')
                for pool in new_pools:
                    pool_dict[pool['id']] = pool

        # print the number of pools with protocol = Sushiswap V2 and Uniswap v2
        '''global sushicount
        global unicount
        for pool in pools:
            # this is where the pools are mapped to their IDs
            # this way they should just replace the old pools rather than being appended forever
            # add the pool to the dictionary by mapping its id to the pool itself
            if pool: 
                pool_dict[pool['id']] = pool
                if pool['protocol'] == 'Sushiswap_V2':
                    sushicount += 1
                elif pool['protocol'] == 'Uniswap V2':
                    unicount += 1
    print(f'number of pools with protocol = Sushiswap V2: {sushicount}')
    print(f'number of pools with protocol = Uniswap V2: {unicount}')
    print(f'number of unique pools: {len(pool_dict)}')'''
    # pools = new_pools
    # await asyncio.sleep(5)

# potentially faster way to flatten the dictionary to a list
'''
import itertools
import multiprocessing

def flatten_dict(pool_dict):
    sub_dicts = (sub_dict for dict_data in pool_dict.values() for dict_id, sub_dict in dict_data.items())
    with multiprocessing.Pool() as pool:
        return list(itertools.chain.from_iterable(pool.imap_unordered(iter, sub_dicts, chunksize=1000)))

flattened_list = flatten_dict(pool_dict)
'''

# filter the pools for the query


def filter_pools(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, exchanges=None, X: int = 100) -> list:
    filtered_pools = []
    full_pools = merge(pools['Uniswap_V2']['pools'], pools['Sushiswap_V2']
                       ['pools'], reverse=True, key=lambda x: float(x[pools[x['protocol']]['metric']]) if x else 0)
    sell_count = 0
    buy_count = 0
    min_count = 10

    for pool in full_pools:
        if not pool or exchanges is not None and pool['protocol'] not in exchanges:
            # print(f'Skipping {pool["protocol"]}')
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
        logging.warning('Insufficient pools cached, using old method')
        logging.warning(
            f'Final buy count: {buy_count}, final sell count: {sell_count}')
        return []

    print(f'sushi count: {sushicount}, uni count: {unicount}')

    return filtered_pools


async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str, exchanges, split=False) -> dict:
    result = {}
    # get the pools
    # pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    filt_pools = filter_pools(sell_symbol, sell_ID,
                              buy_symbol, buy_ID, exchanges=exchanges)
    if len(filt_pools) < 25:
        filt_pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
        filt_pools = [
            pool for pool in filt_pools if pool['protocol'] in exchanges]
    # construct the pool graph
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
    routes = calculate_routes(
        G, valid_paths, sell_amount, sell_symbol, buy_symbol)
    if split:
        final_route = get_final_route(G, routes, sell_amount, sell_symbol)
        result['routes'] = final_route
    else:
        result['routes'] = routes
    # append the routes to the result and return
    '''# save routes to file
    with open('routes.json', 'w') as f:
        json.dump(routes, f)'''
    return result
