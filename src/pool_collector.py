'''
This file contains the functions to get the top X pools for a given token pair.
'''

from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE

# standard library imports
import asyncio
import aiohttp
import sys
import json
from itertools import combinations
import logging

# open the tokens file, a list of the top 1000 tokens by totalVolumeUSD as of 13.12.2022
with open(r'data/uniswap_v2_tokens.json') as f:
    TOKENS = json.load(f)

# Collect the list of bad_tokens
with open(r'data/bad_tokens.json') as f:
    BAD_TOKENS = json.load(f)
    BAD_TOKEN_SYMS = [token['symbol'] for token in BAD_TOKENS['tokens']]

# keeping this here for redundant fallback method, can remove later
ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"

UNISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
UNISWAPV3_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
SUSHISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/sushi-v2/sushiswap-ethereum"
CURVE_ENDPOINT = "https://api.curve.fi/api/getPools/ethereum/main"

# get the top X pools by reserveUSD where token0 = tokenA and token1 = tokenB


async def get_top_pools_token0_token1(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_B), None)

    while True:
        try:
            query = f"""
            {{
            pairs(first: {X}, where: {{token0_: {{symbol: "{symbol_A}", id: "{ID_A}"}}, token1_: {{symbol: "{symbol_B}", id: "{ID_B}"}}}}, orderBy: reserveUSD, orderDirection: desc) {{ 
                id
                reserveUSD
                reserve0
                reserve1
                token0Price
                token1Price
                token0 {{
                    id
                    symbol
                }}
                token1 {{
                    id
                    symbol
                }}
                }}
            }}
            """

            async with aiohttp.ClientSession() as session:
                async with session.post(ENDPOINT, json={'query': query}) as response:
                    obj = await response.json()
                    pools = obj['data']['pairs']
                    return pools

        # this sometimes fails but works on the next try, retry until it works
        except KeyError:
            continue

# get the top X pools by reserveUSD where token0 = tokenA and token1 != tokenB


async def get_top_pools_token0(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_B), None)
    while True:
        try:
            query = f"""
            {{
            pairs(first: {X}, where: {{token0_: {{symbol: "{symbol_A}", id: "{ID_A}"}}, token1_: {{symbol_not: "{symbol_B}", id_not: "{ID_B}"}}}}, orderBy: reserveUSD, orderDirection: desc) {{
                id
                reserveUSD
                reserve0
                reserve1
                token0Price
                token1Price
                token0 {{
                    id
                    symbol
                }}
                token1 {{
                    id
                    symbol
                }}
                }}
            }}
            """

            async with aiohttp.ClientSession() as session:
                async with session.post(ENDPOINT, json={'query': query}) as response:
                    obj = await response.json()
                    pools = obj['data']['pairs']
                    return pools

        # this sometimes fails but works on the next try, retry until it works
        except KeyError:
            continue

# get the top X pools by reserveUSD where token0 != tokenA and token1 = tokenB


async def get_top_pools_token1(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_B), None)
    while True:
        try:
            query = f"""
            {{
            pairs(first: {X}, where: {{token0_: {{symbol_not: "{symbol_A}", id_not: "{ID_A}"}}, token1_: {{symbol: "{symbol_B}", id: "{ID_B}"}}}}, orderBy: reserveUSD, orderDirection: desc) {{
                id
                reserveUSD
                reserve0
                reserve1
                token0Price
                token1Price
                token0 {{
                    id
                    symbol
                }}
                token1 {{
                    id
                    symbol
                }}
                }}
            }}
            """

            async with aiohttp.ClientSession() as session:
                async with session.post(ENDPOINT, json={'query': query}) as response:
                    obj = await response.json()
                    pools = obj['data']['pairs']
                    return pools

        # this sometimes fails but works on the next try, retry until it works
        except KeyError:
            continue


def uniswap_v3_query(X: int, skip: int, max_metric: float):
    if not max_metric:
        return f"""
        {{
        pools(first:1000, skip: {skip}, orderDirection: desc, orderBy: totalValueLockedUSD) {{
            token0 {{
            id
            symbol
            decimals
            }}
            token1 {{
            symbol
            id
            decimals
            }}
            id
            totalValueLockedToken0
            totalValueLockedToken1
            totalValueLockedUSD
            token0Price
            token1Price
            liquidity
            sqrtPrice
        }}
        }}
        """
    else:
        return f"""
        {{
        pools(first:1000, skip: {skip}, orderDirection: desc, orderBy: totalValueLockedUSD, where: {{totalValueLockedUSD_lt: {max_metric}}}) {{
            token0 {{
            id
            symbol
            decimals
            }}
            token1 {{
            symbol
            id
            decimals
            }}
            id
            totalValueLockedToken0
            totalValueLockedToken1
            totalValueLockedUSD
            token0Price
            token1Price
            liquidity
            sqrtPrice
        }}
        }}
        """

async def collect_curve_pools():
    res = []
    async with aiohttp.ClientSession() as session:
        async with session.get(CURVE_ENDPOINT) as response:
            obj = await response.json()
            data = obj['data']['poolData']
            #print(json.dumps(data, indent=4))
            for pool in data:
                pairs = combinations(pool['coins'], 2)
                for pair in pairs:
                    print(f"pool: {pool.get('name', 'NONE')}, pair: {pair[0]['symbol']}-{pair[1]['symbol']}")

                    decimals0 = int(pair[0]['decimals'])
                    decimals1 = int(pair[1]['decimals'])

                    new_pair = {}
                    new_pair['id'] = pool['address'].lower()
                    new_pair['reserve0'] = int(pair[0]['poolBalance']) / 10**decimals0
                    new_pair['reserve1'] = int(pair[1]['poolBalance']) / 10**decimals1
                    new_pair['token0'] = {
                        'id': pair[0]['address'].lower(),
                        'symbol': pair[0]['symbol'],
                        'decimals': decimals0
                    }
                    new_pair['token1'] = {
                        'id': pair[1]['address'].lower(),
                        'symbol': pair[1]['symbol'],
                        'decimals': decimals1
                    }
                    new_pair['token0Price'] = pair[1]['usdPrice'] / pair[0]['usdPrice']
                    new_pair['token1Price'] = pair[0]['usdPrice'] / pair[1]['usdPrice']
                    new_pair['reserveUSD'] = new_pair['reserve0'] * pair[0]['usdPrice'] + new_pair['reserve1'] * pair[1]['usdPrice']
                    new_pair['protocol'] = CURVE
                    new_pair['dangerous'] = new_pair['token0']['symbol'] in BAD_TOKEN_SYMS or new_pair['token1']['symbol'] in BAD_TOKEN_SYMS
                    res.append(new_pair)
    return res

async def get_latest_pool_data(protocol: str, X: int = 1000, skip: int = 0, max_metric: float = None) -> dict:
    # check which endpoint to use, the schema for Uniswap V2 and Sushiswap V2 only differs by the liquidity and reserve metrics
    if protocol == UNISWAP_V2:
        endpoint = UNISWAPV2_ENDPOINT
        orderBy = 'reserveUSD'
        print('collecting data from Uniswap V2...')
        data_field = 'pairs'

    elif protocol == SUSHISWAP_V2:
        endpoint = SUSHISWAPV2_ENDPOINT
        orderBy = 'liquidityUSD'
        print('collecting data from Sushiswap V2...')
        data_field = 'pairs'

    elif protocol == UNISWAP_V3:
        endpoint = UNISWAPV3_ENDPOINT
        print('collecting data from Uniswap V3...')
        data_field = 'pools'

    while True:
        try:
            if protocol == UNISWAP_V3:
                query = uniswap_v3_query(X, skip, max_metric)
            else:
                if not max_metric:
                    query = f"""
                    {{
                    pairs(first: {X}, orderBy: {orderBy}, orderDirection: desc, skip: {skip}) {{
                        id
                        {orderBy}
                        reserve0
                        reserve1
                        token0Price
                        token1Price
                        token0 {{
                            id
                            symbol
                            decimals
                        }}
                        token1 {{
                            id
                            symbol
                            decimals
                        }}
                        }}
                    }}
                    """

                else:
                    query = f"""
                    {{
                    pairs(first: {X}, orderBy: {orderBy}, orderDirection: desc, skip: {skip}, where: {{{orderBy}_lt: {max_metric}}}) {{
                        id
                        {orderBy}
                        reserve0
                        reserve1
                        token0Price
                        token1Price
                        token0 {{
                            id
                            symbol
                            decimals
                        }}
                        token1 {{
                            id
                            symbol
                            decimals
                        }}
                        }}
                    }}
                    """

            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json={'query': query}) as response:
                    obj = await response.json()
                    pools = obj['data'][data_field]

                    # assign protocol name to each pool
                    for pool in pools:
                        pool['dangerous'] = pool['token0']['symbol'] in BAD_TOKEN_SYMS or pool['token1']['symbol'] in BAD_TOKEN_SYMS
                        pool['protocol'] = protocol
                        if protocol == UNISWAP_V3:
                            if pool['sqrtPrice'] == '0':
                                pool = {}
                                continue

                            sqrtPrice = float(pool['sqrtPrice']) / (2 ** 96)
                            liquidity = int(pool['liquidity'])

                            reserve0raw = liquidity / sqrtPrice
                            reserve1raw = liquidity * sqrtPrice

                            reserve0 = reserve0raw / (10 ** int(pool['token0']['decimals']))
                            reserve1 = reserve1raw / (10 ** int(pool['token1']['decimals']))

                            pool['reserve0'] = reserve0
                            pool['reserve1'] = reserve1
                            # print(
                            #     f'Pool calculated reserves: {pool["reserve0"]} {pool["token0"]["symbol"]} and {pool["reserve1"]} {pool["token1"]["symbol"]}')
                            # print(
                            #     f'Pool tvl: {pool["totalValueLockedToken0"]} {pool["token0"]["symbol"]} and {pool["totalValueLockedToken1"]} {pool["token1"]["symbol"]}')

                    # print(query)
                    # print(pools)
                    return pools

        # this sometimes fails but works on the next try, retry until it works
        except KeyError as e:
            print(e)
            continue

        except asyncio.exceptions.TimeoutError as e:
            logging.error("Timeout error while fetching pools")
            continue

        except Exception as e:
            logging.error("Error while fetching pools")
            logging.error(e)
            continue

# get the top X pools by reserveUSD where token0 != symbol_A and token1 != symbol_B


async def get_pool_permutations(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int = 100) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id']
                    for token in TOKENS if token['symbol'] == symbol_B), None)
    while True:
        try:
            # get all permutations of the top X pools, divide by 6 so that we get roughly X pools in total
            tasks = [
                get_top_pools_token0_token1(
                    symbol_A, ID_A, symbol_B, ID_B, int(X/6)),
                get_top_pools_token0_token1(
                    symbol_B, ID_B, symbol_A, ID_A, int(X/6)),
                get_top_pools_token0(symbol_A, ID_A, symbol_B, ID_B, int(X/6)),
                get_top_pools_token1(symbol_A, ID_A, symbol_B, ID_B, int(X/6)),
                get_top_pools_token0(symbol_B, ID_B, symbol_A, ID_A, int(X/6)),
                get_top_pools_token1(symbol_B, ID_B, symbol_A, ID_A, int(X/6))
            ]
            pools = []
            for task in asyncio.as_completed(tasks):
                pools += pools + [x for x in await task if x not in pools]
            # sort the pools by reserveUSD
            pools = sorted(pools, key=lambda x: x['reserveUSD'], reverse=True)
            # add 'protocol': 'Uniswap V2' to each pool
            for pool in pools:
                pool['protocol'] = 'Uniswap_V2'
            '''# save the pools as a json file to /data
            # sort symbol_A and symbol_B alphabetically and use them as the file name
            if symbol_A < symbol_B:
                with open(fr'src/data/{symbol_A}-{symbol_B}.json', 'w') as f:
                    json.dump(pools, f)
            else:  
                with open(fr'src/data/{symbol_B}-{symbol_A}.json', 'w') as f:
                    json.dump(pools, f)'''
            return pools
        # this sometimes fails but works on the next try, retry until it works
        except KeyError:
            continue


# main can be called from another file as follows:
# from pool_collector import get_pool_permutations
# pools = asyncio.run(get_pool_permutations('USDC', None, 'DAI', None, 100))
async def main():
    # get the list of tokens from the command line
    tokens = sys.argv[1].split(',')
    # get the search size from the command line
    X = int(sys.argv[2])
    # get the list of pools
    pools = await get_pool_permutations(tokens[0], tokens[1], X)
    # print the list of pools
    print(pools)

if __name__ == '__main__':
    # only need this if running on windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
