'''
This module contains the main function for the smart order router, calling all the other relevant modules.
'''

# local imports
from pool_collector import get_latest_pool_data, collect_curve_pools, reformat_balancer_v1_pools, reformat_balancer_v2_pools
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route
# third party imports
import logging
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V1, BALANCER_V2, DODO, PANCAKESWAP_V3, MAX_ROUTES
from heapq import merge
import json
import time
# import dotenv
# import os
# import requests


'''# load coinmarketcap api key from .env
dotenv.load_dotenv()
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")'''

MAX_ORDERS = 20

DEX_LIST = (
    UNISWAP_V2,
    UNISWAP_V3,
    SUSHISWAP_V2,
    CURVE,
    BALANCER_V1,
    BALANCER_V2,
    DODO,
    PANCAKESWAP_V3
)

DEX_METRIC_MAP = {
    UNISWAP_V2: 'reserveUSD',
    UNISWAP_V3: 'totalValueLockedUSD',
    SUSHISWAP_V2: 'liquidityUSD',
    CURVE: 'reserveUSD',
    BALANCER_V1: 'liquidity',
    BALANCER_V2: 'totalLiquidity',
    DODO: 'volumeUSD',
    PANCAKESWAP_V3: 'totalValueLockedUSD'
}

DEX_LIQUIDITY_METRIC_MAP = {
    UNISWAP_V2: 'reserveUSD',
    UNISWAP_V3: 'totalValueLockedUSD',
    SUSHISWAP_V2: 'liquidityUSD',
    CURVE: 'reserveUSD',
    BALANCER_V1: 'reserveUSD',
    BALANCER_V2: 'reserveUSD',
    DODO: 'reserveUSD',
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
            token0_id = pool['token0']['id']
            token1_id = pool['token1']['id']
            key = f"{pool['id']}_{token0_id}_{token1_id}"
            pool_dict[key] = pool
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
                if protocol == BALANCER_V1:
                    new_balancer_pools = reformat_balancer_v1_pools(new_pools)
                    for pool in new_balancer_pools:
                        token0_id = pool['token0']['id']
                        token1_id = pool['token1']['id']
                        key = f"{pool['id']}_{token0_id}_{token1_id}"
                        pool_dict[key] = pool
                        pools[protocol]['pools'].append(pool) 
                elif protocol == BALANCER_V2:
                    new_balancer_pools = reformat_balancer_v2_pools(new_pools)
                    for pool in new_balancer_pools:
                        token0_id = pool['token0']['id']
                        token1_id = pool['token1']['id']
                        key = f"{pool['id']}_{token0_id}_{token1_id}"
                        pool_dict[key] = pool
                        pools[protocol]['pools'].append(pool)
                else:
                    for pool in new_pools:
                        token0_id = pool['token0']['id']
                        token1_id = pool['token1']['id']
                        key = f"{pool['id']}_{token0_id}_{token1_id}"
                        pool_dict[key] = pool
                        pools[protocol]['pools'].append(pool)  

                print("Total pairs collected: "+str(len(pool_dict)))
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


'''def get_token_price_usd(symbol, convert_to_symbol="USD"):
    url = f"https://pro-api.coinmarketcap.com/v1/tools/price-conversion?amount=1&symbol={symbol}&convert={convert_to_symbol}"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY
    }
    response = requests.get(url, headers=headers)
    response_data = json.loads(response.text)
    return response_data["data"]["quote"][convert_to_symbol]["price"]'''

def get_token_price_usd(token_id):
    global pool_dict
    pools_with_token = [pool for pool in pool_dict.values() if token_id in (pool['token0']['id'], pool['token1']['id'])]
    total_price_usd = 0.0
    num_pools = 0
    for pool in pools_with_token:
        token0_price_usd = float(pool['token0'].get('priceUSD', 0))
        token1_price_usd = float(pool['token1'].get('priceUSD', 0))
        total_price_usd += token0_price_usd + token1_price_usd
        num_pools += 2
    average_price_usd = total_price_usd / num_pools if num_pools > 0 else 0.0
    return average_price_usd

def find_max_liquidity(pool_dict, n=10):
    most_liquid_pools = sorted(pool_dict.items(), key=lambda x: float(x[1][DEX_LIQUIDITY_METRIC_MAP[x[1]['protocol']]]), reverse=True)[:n]
    return float(most_liquid_pools[0][1][DEX_LIQUIDITY_METRIC_MAP[most_liquid_pools[0][1]['protocol']]])

def find_max_price(pool_dict, n=10):
    most_expensive_pools = sorted(pool_dict.items(), key=lambda x: max(float(x[1]['token0'].get('priceUSD', 0)), float(x[1]['token1'].get('priceUSD', 0))), reverse=True)[:n]
    return max(float(most_expensive_pools[0][1]['token0'].get('priceUSD', 0)), float(most_expensive_pools[0][1]['token1'].get('priceUSD', 0)))

def calculate_score(pool, trade_value, max_trade_value, max_price, max_liquidity):
    # Normalize the factors
    normalized_price = max(float(pool['token0'].get('priceUSD', 0)), float(pool['token1'].get('priceUSD', 0))) / max_price
    normalized_liquidity = float(pool[DEX_LIQUIDITY_METRIC_MAP[pool['protocol']]]) / max_liquidity

    # Adjust the weights based on the trade value
    w1 = trade_value / max_trade_value  # Liquidity weight increases with trade value
    w2 = 1 - w1  # Price weight decreases with trade value

    # Calculate the score
    # score = w1 * normalized_liquidity + w2 * normalized_price
    score = normalized_liquidity 

    return score

def filter_pools_best_match(sell_symbol: str, sell_ID: str, sell_amount: float, exchanges=None, X: int = 30, Y: int = 30):
    global pool_dict
    # Calculate trade value
    avg_sell_token_price_usd = get_token_price_usd(sell_ID) # placeholder until we get the actual price in a better way
    trade_value = sell_amount * avg_sell_token_price_usd
    max_trade_value = 100000000  # Arbitrarily set
    
    # Get max_price and max_liquidity from all pools
    max_price = find_max_price(pool_dict)
    max_liquidity = find_max_liquidity(pool_dict)
    
    pool_scores = []
    for pool in pool_dict.values():
        # Exclude pools whose exchange is not in the exchanges list
        if exchanges is not None and pool['protocol'] not in exchanges:
            continue
        
        # Calculate pool score
        score = calculate_score(pool, trade_value, max_trade_value, max_price, max_liquidity)
        pool_scores.append((pool, score))

    # Sort the pools based on score
    sorted_pool_scores = sorted(pool_scores, key=lambda x: x[1], reverse=True)
    # Get the top X pools by score
    top_X_pools = [pool_score[0] for pool_score in sorted_pool_scores[:X]]
    # Get the top Y pools that contain the sell_token
    top_Y_sell_token_pools = [pool_score[0] for pool_score in sorted_pool_scores if sell_ID in (pool_score[0]['token0']['id'], pool_score[0]['token1']['id'])][:Y]
    # Return a list combining the two sets of pools
    return top_X_pools + top_Y_sell_token_pools

async def route_orders(sell_symbol: str, sell_ID: str, sell_amount: float, buy_symbol: str, buy_ID: str, exchanges, split=False, routing_strategy='default') -> dict:
    result = {}
    
    # get the pools
    if routing_strategy == 'best_match':
        filt_pools = filter_pools_best_match(sell_symbol, sell_ID, sell_amount, exchanges=exchanges)
        # fallback in case arg management in server.py fails
        buy_symbol = sell_symbol
        buy_ID = sell_ID
    else:
        filt_pools = filter_pools(sell_symbol, sell_ID, buy_symbol, buy_ID, exchanges=exchanges)
    
    if len(filt_pools) < 5:
        time.sleep(5)
        filter_pools(sell_symbol, sell_ID, buy_symbol, buy_ID, exchanges=DEX_LIST)
    
    # construct the pool graph
    G = construct_pool_graph(filt_pools)
    # get the graph dict
    graph_dict = pool_graph_to_dict(G)
    # append the dict to the result
    result['pool_graph'] = graph_dict
    # find the shortest paths
    paths = find_shortest_paths(G, sell_symbol, buy_symbol)
    # validate the paths
    if routing_strategy == 'best_match': # all paths are valid if it doesn't matter what our output token is, any paths that somehow still involve selling a token to a pool not accepted will be filtered out by the price impact calculation anyway
        valid_paths = paths
    else:
        valid_paths = validate_all_paths(G, paths, sell_ID, buy_ID)
    # create the path graph
    path_graph = create_path_graph(valid_paths)
    # get the path graph dict
    path_graph_dict = path_graph_to_dict(path_graph)
    # append the dict to the result
    result['path_graph'] = path_graph_dict
    # calculate the routes (traverse the paths and calculate price impact at each swap)
    routes = calculate_routes(G, valid_paths, sell_amount, sell_symbol, buy_symbol)

    # Loop over routes and calculate price_usd and amount_out_usd
    for route_name, route_dict in routes:
        # Get the swap keys
        swap_keys = [key for key in route_dict.keys() if "swap_" in key]
        # Sort the keys by the number following 'swap_'
        swap_keys.sort(key=lambda x: int(x.split('_')[1]))
        # Get the last swap key
        last_swap_key = swap_keys[-1]
        # Get the last swap
        last_swap = route_dict[last_swap_key]
        # Get the output token and pool ID
        output_token = last_swap['output_token']
        pool_id = last_swap['pool']
        # Retrieve the pool information
        pool = G.nodes[pool_id]['pool']  # assuming that the pool data is contained within G
        # Find the price in USD for the output token
        price_usd = None
        if pool['token0']['symbol'] == output_token:
            price_usd = float(pool['token0']['priceUSD'])
        elif pool['token1']['symbol'] == output_token:
            price_usd = float(pool['token1']['priceUSD'])
        # Calculate the amount out in USD
        amount_out_usd = price_usd * float(last_swap['output_amount'])
        # Add these to the route dictionary
        route_dict['price_usd'] = price_usd
        route_dict['amount_out_usd'] = amount_out_usd

    if routing_strategy == 'best_match':
        # Sort the routes by amount_out_usd
        routes.sort(key=lambda x: x[1]['amount_out_usd'], reverse=True)

    if split:
        final_route = get_final_route(G, routes, sell_amount, sell_symbol)
        result['routes'] = final_route
    else:
        result['routes'] = routes[:MAX_ROUTES]

    return result
