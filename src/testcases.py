'''
This file is for testing functions without having to run the entire smart order router.
'''

# local imports
from pool_collector import get_latest_pool_data, get_pool_permutations, collect_curve_pools, reformat_balancer_pools
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route
from smart_order_router import refresh_pools, DEX_LIST, DEX_METRIC_MAP, BLACKLISTED_TOKENS, pool_dict, pools
import logging
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V2, MAX_ROUTES
from heapq import merge
import json
import asyncio

MAX_ORDERS = 20

DEX_LIST = (
    CURVE,
    UNISWAP_V3,
    UNISWAP_V2,
    SUSHISWAP_V2,
    BALANCER_V2
)

DEX_METRIC_MAP = {
    UNISWAP_V2: 'reserveUSD',
    UNISWAP_V3: 'totalValueLockedUSD',
    SUSHISWAP_V2: 'liquidityUSD',
    CURVE: 'reserveUSD',
    BALANCER_V2: 'liquidity'
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


# filter the pools for the query
def filter_pools(sell_symbol: str, sell_ID: str, buy_symbol: str, buy_ID: str, exchanges=None, X: int = 50) -> list:
    if exchanges is None:
        exchanges = DEX_LIST
    # Add this print statement
    for protocol in DEX_LIST:
        print(f"{protocol} pool count: {len([pool for pool in pools[protocol]['pools'] if pool is not None])}")

    filtered_pools = []
    full_pools = merge(*[pools[protocol]['pools'] for protocol in DEX_LIST], reverse=True, key=lambda x: float(x[pools[x['protocol']]['metric']]) if x else 0)
    sell_count = 0
    buy_count = 0
    min_count = 1

    for pool in full_pools:
        # print(f'exchanges: {exchanges}, type: {type(exchanges)}')
        if (not pool) or (exchanges is not None and pool['protocol'] not in exchanges):
            # if pool:
                # print(f'{pool["protocol"]} not in {exchanges}, skipping...')
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

    # print the number of protocols in the filtered pools
    protocols = set([pool['protocol'] for pool in filtered_pools])
    print(f'protocols in filtered pools: {protocols}')

    return filtered_pools


async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str, exchanges, split=False) -> dict:
    result = {}
    # get the pools
    # pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
    filt_pools = filter_pools(sell_symbol, sell_ID,
                              buy_symbol, buy_ID, exchanges=exchanges)
    if len(filt_pools) < 5:
        filt_pools = await get_pool_permutations(sell_symbol, sell_ID, buy_symbol, buy_ID)
        filt_pools = [
            pool for pool in filt_pools if pool['protocol'] in exchanges]
    # print(json.dumps(filt_pools, indent=4))
    # construct the pool graph
    G = construct_pool_graph(filt_pools)
    # get the graph dict
    graph_dict = pool_graph_to_dict(G)
    # save the graph dict to test results
    with open('test_results/graph_dict.json', 'w') as f:
        json.dump(graph_dict, f)
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


async def main():
    # get the latest pool data 
    print("testing collection, getting latest pool data...")

    refresh_tasks = [refresh_pools(dex) for dex in DEX_LIST]
    try:
        await asyncio.gather(*refresh_tasks)
    except KeyboardInterrupt:
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        await asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)

    # save the pool data
    with open('test_results\\pool_dict.json', 'w') as f:
        json.dump(pool_dict, f)
    with open('test_results\\pools.json', 'w') as f:
        json.dump(pools, f)
    
    # filter for:
    sell_id = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    sell_symbol = 'WETH'
    buy_id = '0x6b175474e89094c44da98b954eedeac495271d0f'
    buy_symbol = 'DAI'

    '''print(f"testing filtering for {sell_symbol} -> {buy_symbol}... on {DEX_LIST}")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=[UNISWAP_V3, UNISWAP_V2, SUSHISWAP_V2, CURVE, BALANCER_V2])
    # save the filtered pools
    with open('test_results\\filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {DEX_LIST}")
    # test route orders with the same parameters
    routes = await route_orders(sell_symbol, sell_id, 1000, buy_symbol, buy_id, exchanges=[UNISWAP_V3, UNISWAP_V2, SUSHISWAP_V2, CURVE, BALANCER_V2], split=False)

    print(f"testing splitting for {sell_symbol} -> {buy_symbol}... on {DEX_LIST}")
    # test route orders with the same parameters
    split_routes = await route_orders(sell_symbol, sell_id, 1000, buy_symbol, buy_id, exchanges=[UNISWAP_V3, UNISWAP_V2, SUSHISWAP_V2, CURVE, BALANCER_V2], split=True)

    # save the routes
    with open('test_results\\routes.json', 'w') as f:
        json.dump(routes, f)

    # save the split routes
    with open('test_results\\split_routes.json', 'w') as f:
        json.dump(split_routes, f)'''

    # test for balancer only
    print(f"testing filtering for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=BALANCER_V2)
    # save the filtered pools
    with open('test_results\\balancer_filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    routes = await route_orders(sell_symbol, sell_id, 100, buy_symbol, buy_id, exchanges=BALANCER_V2, split=False)

    print(f"testing splitting for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    split_routes = await route_orders(sell_symbol, sell_id, 10, buy_symbol, buy_id, exchanges=BALANCER_V2, split=True)

    # save the routes
    with open('test_results\\balancer_routes.json', 'w') as f:
        json.dump(routes, f)

    # save the split routes 
    with open('test_results\\balancer_split_routes.json', 'w') as f:
        json.dump(split_routes, f)
    

if __name__ == '__main__':
    asyncio.run(main())
