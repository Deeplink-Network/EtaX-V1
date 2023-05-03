'''
This file handles the querying of liquidity pool data from various DEXs.
'''

# locla utility imports
from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V2, DODO, PANCAKESWAP_V3

# standard library imports
import asyncio
import aiohttp
import sys
import json
from itertools import combinations
import logging

# Collect the list of bad_tokens
with open(r'data/bad_tokens.json') as f:
    BAD_TOKENS = json.load(f)
    BAD_TOKEN_SYMS = [token['symbol'] for token in BAD_TOKENS['tokens']]

UNISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
UNISWAPV3_ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
SUSHISWAPV2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/sushi-v2/sushiswap-ethereum"
CURVE_ENDPOINT = "https://api.curve.fi/api/getPools/ethereum/main"
BALANCER_V2_ENDPOINT = "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer"
DODO_ENDPOINT = "https://api.thegraph.com/subgraphs/name/dodoex/dodoex-v2"
PANCAKESWAP_V3_ENDPOINT = "https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v3-eth"

def pancakeswap_v3_query(X: int, skip: int, max_metric: float):
    if not max_metric:
        return f"""
        {{
        pools(first: {X}, skip: {skip}, orderDirection: desc, orderBy: totalValueLockedUSD) {{
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
            feeTier
            sqrtPrice
        }}
        }}
        """
    else:
        return f"""
        {{
        pools(first: {X}, skip: {skip}, orderDirection: desc, orderBy: totalValueLockedUSD, where: {{totalValueLockedUSD_lt: {max_metric}}}) {{
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
            feeTier
            sqrtPrice
        }}
        }}
        """

        
def dodo_query(X: int, skip: int, max_metric: float):
    if not max_metric:
        return f"""
        {{
        pairs(first: {X}, orderBy: volumeUSD, orderDirection: desc, skip: {skip}, where:{{type_not: "VIRTUAL"}}) {{
            baseReserve
            baseToken {{
            decimals
            id
            name
            usdPrice
            symbol
            }}
            i
            id
            feeUSD
            feeBase
            feeQuote
            k
            lastTradePrice
            quoteReserve
            quoteToken {{
            decimals
            id
            name
            usdPrice
            symbol
            }}
            volumeUSD
            type
        }}
        }}
        """
    else:
        return f"""
        {{
        pairs(first: {X}, orderBy: volumeUSD, orderDirection: desc, skip: {skip}, where: {{volumeUSD_lt: {max_metric}, type_not: "VIRTUAL"}}) {{
            baseReserve
            baseToken {{
            decimals
            id
            name
            usdPrice
            symbol
            }}
            i
            id
            feeUSD
            feeBase
            feeQuote
            k
            lastTradePrice
            quoteReserve
            quoteToken {{
            decimals
            id
            name
            usdPrice
            symbol
            }}
            volumeUSD
            type
        }}
        }}
        """

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
    

def balancer_v2_query(X: int, skip: int, max_metric: float):
    if not max_metric:
        return f"""
        {{
        pools(first: {X}, orderBy: liquidity, orderDirection: desc, skip: {skip}) {{
            id
            liquidity
            swapFee
            tokensList
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
        return f"""
        {{
        pools(first: {X}, orderBy: liquidity, orderDirection: desc, skip: {skip}, where: {{liquidity_lt: {max_metric}}}) {{
            id
            liquidity
            swapFee
            tokensList
            tokens(orderBy: address) {{
                address
                balance
                symbol
                denormWeight
            }}
            }}
        }}
        """
        

# reformat balancer helper function
def reformat_balancer_pools(pool_list):
    ''' Reformats a list of balancer pools into the uniswap/sushiswap format. '''
    # Define a helper function to reformat a single pool
    def reformat_pool(pool):
        # Get all combinations of two tokens in the balancer pool
        token_combinations = list(combinations(pool['tokens'], 2))
        # Initialize a list to hold the dictionaries for each uniswap pool
        reformatted_pools = []
        # Iterate over each token combination and create a corresponding uniswap pool dictionary
        for combination in token_combinations:
            token0 = combination[0]
            token1 = combination[1]
            new_pair = {
                'id': pool['id'],
                'liquidity': pool['liquidity'],
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
                'protocol': 'Balancer_V2',
            }
            reformatted_pools.append(new_pair)
            new_pair['dangerous'] = new_pair['token0']['symbol'] in BAD_TOKEN_SYMS or new_pair['token1']['symbol'] in BAD_TOKEN_SYMS
        return reformatted_pools
    # Initialize a list to hold all reformatted pools
    all_reformatted_pools = []
    # Iterate over each pool and reformat it
    for pool in pool_list:
        reformatted_pools = reformat_pool(pool)
        all_reformatted_pools.extend(reformatted_pools)
    return all_reformatted_pools


async def collect_curve_pools():
    print('collecting data from curve...')
    res = []
    async with aiohttp.ClientSession() as session:
        async with session.get(CURVE_ENDPOINT) as response:
            obj = await response.json()
            data = obj['data']['poolData']
            #print(json.dumps(data, indent=4))
            for pool in data:
                try:
                    pairs = combinations(pool['coins'], 2)
                    for pair in pairs:
                        # Check if either usdPrice is None and skip this pair if true
                        if pair[0]['usdPrice'] is None or pair[1]['usdPrice'] is None:
                            continue
                        # print(f"pool: {pool.get('name', 'NONE')}, pair: {pair[0]['symbol']}-{pair[1]['symbol']}")

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
                except Exception as e:
                    print(e)
                    print(pool)
                    break
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
    elif protocol == BALANCER_V2:
        endpoint = BALANCER_V2_ENDPOINT
        print('collecting data from Balancer V2...')
        data_field = 'pools'
    elif protocol == DODO:
        endpoint = DODO_ENDPOINT
        print('collecting data from DODO...')
        data_field = 'pairs'
    elif protocol == PANCAKESWAP_V3:
        endpoint = PANCAKESWAP_V3_ENDPOINT
        print('collecting data from Pancakeswap V3...')
        data_field = 'pools'
    while True:
        try:
            if protocol == UNISWAP_V3:
                query = uniswap_v3_query(X, skip, max_metric)
            elif protocol == BALANCER_V2:
                query = balancer_v2_query(X, skip, max_metric)
            elif protocol == DODO:
                query = dodo_query(X, skip, max_metric)
            elif protocol == PANCAKESWAP_V3:
                query = pancakeswap_v3_query(X, skip, max_metric)
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
                    # pool processing
                    for pool in pools:
                        pool['protocol'] = protocol
                        if protocol == PANCAKESWAP_V3:
                            pool['reserve0'] = pool.pop('totalValueLockedToken0')
                            pool['reserve1'] = pool.pop('totalValueLockedToken1')
                        if protocol == UNISWAP_V3:
                            if pool['sqrtPrice'] == '0':
                                pool['reserve0'] = 0
                                pool['reserve1'] = 0
                                continue
                            sqrtPrice = float(pool['sqrtPrice']) / (2 ** 96)
                            liquidity = int(pool['liquidity'])
                            reserve0raw = liquidity / sqrtPrice
                            reserve1raw = liquidity * sqrtPrice
                            reserve0 = reserve0raw / (10 ** int(pool['token0']['decimals']))
                            reserve1 = reserve1raw / (10 ** int(pool['token1']['decimals']))
                            pool['reserve0'] = reserve0
                            pool['reserve1'] = reserve1
                        if protocol == DODO:
                            # volumeUSD doesn't seem to be accurate for DODO, augment a reserveUSD metric for sorting
                            pool['reserveUSD'] = float(pool['quoteReserve']) * float(pool['quoteToken']['usdPrice']) + float(pool['baseReserve']) * float(pool['baseToken']['usdPrice'])
                            # rename fields to match other protocols, base = 0 and quote = 1
                            pool['token0'] = pool.pop('baseToken')
                            pool['token1'] = pool.pop('quoteToken')
                            pool['reserve0'] = pool.pop('baseReserve')
                            pool['reserve1'] = pool.pop('quoteReserve')
                            pool['token0Price'] = float(pool['lastTradePrice'])
                            try:
                                pool['token1Price'] = 1 / float(pool['lastTradePrice'])
                            except:
                                pool['token1Price'] = 0
                        pool['dangerous'] = (
                            (protocol != BALANCER_V2 and (
                                pool['token0']['symbol'] in BAD_TOKEN_SYMS or
                                pool['token1']['symbol'] in BAD_TOKEN_SYMS or
                                pool['reserve0'] == 0 or
                                pool['reserve1'] == 0
                            )) or
                            (protocol == BALANCER_V2 and any(
                                token['symbol'] in BAD_TOKEN_SYMS for token in pool['tokens']
                            ))
                        )

                    return pools
        # this sometimes fails but works on the next try, retry until it works
        except KeyError as e:
            print()
            print(query)
            print(e)
            print()
            continue
        except asyncio.exceptions.TimeoutError as e:
            logging.error("Timeout error while fetching pools")
            continue
        except Exception as e:
            logging.error("Error while fetching pools")
            logging.error(e)
            continue