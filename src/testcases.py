'''
This file is for testing functions without having to run the entire smart order router.
'''

# local imports
from pool_collector import get_latest_pool_data, collect_curve_pools, reformat_balancer_v1_pools
from smart_order_router import refresh_pools, filter_pools, pools, pool_dict, DEX_LIST, DEX_METRIC_MAP, route_orders
# third party imports
import logging
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V1, BALANCER_V2, DODO, PANCAKESWAP_V3, MAX_ROUTES
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
    sell_amount = 1

    for exchange in DEX_LIST:
        print(f"testing filtering for {sell_symbol} -> {buy_symbol} on {exchange}...")
        filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=DEX_LIST)

        # save the filtered pools
        with open(f'test_results\\{exchange}_filtered_pools.json', 'w') as f:
            json.dump(filtered_pools, f)

        print(f"testing routing for {sell_symbol} -> {buy_symbol}... on {exchange}")
        routes = await route_orders(sell_symbol, sell_id, sell_amount, buy_symbol, buy_id, exchanges=exchange, split=False)

        print(f"testing route splitting for {sell_symbol} -> {buy_symbol}... on {exchange}")
        split_routes = await route_orders(sell_symbol, sell_id, sell_amount, buy_symbol, buy_id, exchanges=exchange, split=True)

        # save the routes
        with open(f'test_results\\{exchange}_routes.json', 'w') as f:
            json.dump(routes, f)

        # save the split routes
        with open(f'test_results\\{exchange}_split_routes.json', 'w') as f:
            json.dump(split_routes, f)

    # test once more for all exchanges
    print(f"testing filtering for {sell_symbol} -> {buy_symbol} on all exchanges...")
    filtered_pools = filter_pools(sell_symbol, sell_id, buy_symbol, buy_id, exchanges=DEX_LIST)

    # save the filtered pools
    with open(f'test_results\\all_filtered_pools.json', 'w') as f:
        json.dump(filtered_pools, f)

    print(f"testing routing for {sell_symbol} -> {buy_symbol}... on all exchanges")
    routes = await route_orders(sell_symbol, sell_id, sell_amount, buy_symbol, buy_id, exchanges=DEX_LIST, split=False)

    print(f"testing route splitting for {sell_symbol} -> {buy_symbol}... on all exchanges")
    split_routes = await route_orders(sell_symbol, sell_id, sell_amount, buy_symbol, buy_id, exchanges=DEX_LIST, split=True)

    # save the routes
    with open(f'test_results\\all_routes.json', 'w') as f:
        json.dump(routes, f)

    # save the split routes
    with open(f'test_results\\all_split_routes.json', 'w') as f:
        json.dump(split_routes, f)


if __name__ == "__main__":
    asyncio.run(main())