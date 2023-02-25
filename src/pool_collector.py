'''
This file contains the functions to get the top X pools for a given token pair.
'''

from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, BALANCER_V1

# standard library imports
import asyncio
import aiohttp
import sys
import json
from math import sqrt
import itertools

# open the tokens file, a list of the top 1000 tokens by totalVolumeUSD as of 13.12.2022
with open(r'data/uniswap_v2_tokens.json') as f:
    TOKENS = json.load(f)

# keeping this here for redundant fallback method, can remove later
ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"

UNISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
UNISWAPV3_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
SUSHISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/sushi-v2/sushiswap-ethereum"
BALANCERV1_ENDPOINT = "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer"

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

def balancer_v1_query(X: int, skip: int, max_metric: float = None):
    if not max_metric:
        query = f"""
        {{
            pools(first: {X}, orderBy: liquidity, orderDirection: desc) {{
                id
                liquidity
                swapFee
                tokens(orderBy: address) {{
                    address
                    balance
                    symbol
                    denormWeight
                }}
            }}
        }}
        """
    else:
        query = f"""
        {{
            pools(first: {X}, orderBy: liquidity, orderDirection: desc, where: {{liquidity_lt: {max_metric}}}) {{
                id
                liquidity
                swapFee
                tokens(orderBy: address) {{
                    address
                    balance
                    symbol
                    denormWeight
                }}
            }}
        }}
        """
    return query

    
# reformat balancer helper function
def reformat_balancer_pools(pool_list):
    ''' Reformats a list of balancer pools into the uniswap/sushiswap format. '''
    # Define a helper function to reformat a single pool
    def reformat_pool(pool):
        # Get all combinations of two tokens in the balancer pool
        token_combinations = list(itertools.combinations(pool['tokens'], 2))

        # Initialize a list to hold the dictionaries for each uniswap pool
        reformatted_pools = []

        # Iterate over each token combination and create a corresponding uniswap pool dictionary
        for combination in token_combinations:
            token0 = combination[0]
            token1 = combination[1]
            pool_dict = {
                'id': pool['id'],
                'liquidityUSD': pool['liquidity'],
                'swapFee': pool['swapFee'],
                'reserve0': token0['balance'],
                'reserve1': token1['balance'],
                'token0': {
                    'id': token0['address'],
                    'symbol': token0['symbol'],
                    'denormWeight': token0['denormWeight']
                },
                'token1': {
                    'id': token1['address'],
                    'symbol': token1['symbol'],
                    'denormWeight': token1['denormWeight']
                },
                'protocol': 'Balancer_V1',
            }
            reformatted_pools.append(pool_dict)
        return reformatted_pools

    # Initialize a list to hold all reformatted pools
    all_reformatted_pools = []

    # Iterate over each pool and reformat it
    for pool in pool_list:
        reformatted_pools = reformat_pool(pool)
        all_reformatted_pools.extend(reformatted_pools)

    return all_reformatted_pools

async def get_latest_pool_data(protocol: str, X: int = 1000, skip: int = 0, max_metric: float = None) -> dict:
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
    elif protocol == BALANCER_V1:
        endpoint = BALANCERV1_ENDPOINT
        print('collecting data from Balancer V1...')
        data_field = 'pools'

    while True:
        try:
            if protocol == UNISWAP_V3:
                query = uniswap_v3_query(X, skip, max_metric)
            elif protocol == BALANCER_V1:
                query = balancer_v1_query(X, skip, max_metric)
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

                        elif protocol == BALANCER_V1:
                            reformatted_pools = reformat_balancer_pools([pool])
                            pools = reformatted_pools

                    return pools
        except KeyError as e:
            print(e)
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
