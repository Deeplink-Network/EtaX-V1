'''
This file is for testing functions without having to run the entire smart order router.
'''

# local imports
from pool_collector import get_latest_pool_data, collect_curve_pools, reformat_balancer_pools
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route
from smart_order_router import refresh_pools, filter_pools, pools, pool_dict, DEX_LIST, DEX_METRIC_MAP, route_orders
# third party imports
import logging
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V2, DODO, PANCAKESWAP_V3, MAX_ROUTES
from heapq import merge
import json
import asyncio


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
    sell_id = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    sell_symbol = 'USDC'
    buy_id = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    buy_symbol = 'WETH'

    '''# test for DODO only
    print(f"testing filtering for {sell_symbol} -> {buy_symbol}... on {DODO}")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=DODO)
    # save the filtered pools
    with open('test_results\\DODO_filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {DODO}")
    routes = await route_orders(sell_symbol, sell_id, 100_000, buy_symbol, buy_id, exchanges=DODO, split=False)

    print(f"testing route splitting for {sell_symbol} -> {buy_symbol}... on {DODO}")
    split_routes = await route_orders(sell_symbol, sell_id, 100_000, buy_symbol, buy_id, exchanges=DODO, split=True)

    # save the routes
    with open('test_results\\DODO_routes.json', 'w') as f:
        json.dump(routes, f)

    with open('test_results\\DODO_split_routes.json', 'w') as f:
        json.dump(split_routes, f)'''

    # test for Pancake only
    print(f"testing filtering for {sell_symbol} -> {buy_symbol}... on {PANCAKESWAP_V3}")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=PANCAKESWAP_V3)
    # save the filtered pools
    with open('test_results\\PANCAKESWAP_V3_filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {PANCAKESWAP_V3}")
    routes = await route_orders(sell_symbol, sell_id, 100, buy_symbol, buy_id, exchanges=PANCAKESWAP_V3, split=False)

    print(f"testing route splitting for {sell_symbol} -> {buy_symbol}... on {PANCAKESWAP_V3}")
    split_routes = await route_orders(sell_symbol, sell_id, 100, buy_symbol, buy_id, exchanges=PANCAKESWAP_V3, split=True)

    # save the routes
    with open('test_results\\PANCAKESWAP_V3_routes.json', 'w') as f:
        json.dump(routes, f)

    # save the split routes 
    with open('test_results\\PANCAKESWAP_V3_split_routes.json', 'w') as f:
        json.dump(split_routes, f)

    '''# repeat the routing tests for Balancer
    print(f"testing filtering for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=BALANCER_V2)
    # save the filtered pools
    with open('test_results\\BALANCER_filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    routes = await route_orders(sell_symbol, sell_id, 100, buy_symbol, buy_id, exchanges=BALANCER_V2, split=False)

    print(f"testing route splitting for {sell_symbol} -> {buy_symbol}... on {BALANCER_V2}")
    split_routes = await route_orders(sell_symbol, sell_id, 100, buy_symbol, buy_id, exchanges=BALANCER_V2, split=True)

    # save the routes
    with open('test_results\\BALANCER_routes.json', 'w') as f:
        json.dump(routes, f)

    # save the split routes
    with open('test_results\\BALANCER_split_routes.json', 'w') as f:
        json.dump(split_routes, f)'''
    

if __name__ == '__main__':
    asyncio.run(main())
