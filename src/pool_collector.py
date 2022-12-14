'''
This file contains the functions to get the top X pools for a given token pair.
'''

# standard library imports
import asyncio 
import aiohttp
import sys
import json

# open the tokens file, a list of the top 1000 tokens by totalVolumeUSD as of 13.12.2022
with open(r'src\data\uniswap_v2_tokens.json') as f:
    TOKENS = json.load(f)

ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"

# get the top X pools by reserveUSD where token0 = tokenA and token1 = tokenB
async def get_top_pools_token0_token1(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id'] for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id'] for token in TOKENS if token['symbol'] == symbol_B), None)
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
        ID_A = next((token['id'] for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id'] for token in TOKENS if token['symbol'] == symbol_B), None)
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
        ID_A = next((token['id'] for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id'] for token in TOKENS if token['symbol'] == symbol_B), None)
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

# get the top X pools by reserveUSD where token0 != symbol_A and token1 != symbol_B
async def get_pool_permutations(symbol_A: str, ID_A: str, symbol_B: str, ID_B: str, X: int=100) -> dict:
    # if the ID is not provided, find it
    if ID_A == None or ID_B == None:
        ID_A = next((token['id'] for token in TOKENS if token['symbol'] == symbol_A), None)
        ID_B = next((token['id'] for token in TOKENS if token['symbol'] == symbol_B), None)
    while True:
        try:
            # get all permutations of the top X pools, divide by 6 so that we get roughly X pools in total
            tasks = [
                get_top_pools_token0_token1(symbol_A, ID_A, symbol_B, ID_B, int(X/6)),
                get_top_pools_token0_token1(symbol_B, ID_B, symbol_A, ID_A, int(X/6)),
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
                pool['protocol'] = 'Uniswap V2'
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
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # only need this if running on windows
    asyncio.run(main())