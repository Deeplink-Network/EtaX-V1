'''
This script collects the top 1000 Uniswap V2 tokens ordered descending by tradeVolumeUSD, it is not used in the final product but was used to get the top 1000 tokens for the graph_constructor.py script.
'''

# standard library imports
import asyncio
import aiohttp
import json

ENDPOINT = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"

# query and save the top 1000 Uniswap V2 tokens ordered descending by tradeVolumeUSD
async def get_top_tokens(order: str) -> dict:
    while True:
        try:
            query = f"""
            {{
            tokens(first: 1000, orderBy: tradeVolumeUSD, orderDirection: {order}) {{
                id
                symbol
                name
                tradeVolumeUSD
                }}
            }}
            """
            
            async with aiohttp.ClientSession() as session:
                async with session.post(ENDPOINT, json={'query': query}) as response:
                    obj = await response.json()
                    tokens = obj['data']['tokens']
                    return tokens
        
        # this sometimes fails but works on the next try, retry until it works
        except KeyError:
            continue

# main function
async def main():
    tokens = await get_top_tokens('desc')
    # save tokens to a JSON file
    with open('uniswap_v2_tokens.json', 'w') as f:
        json.dump(tokens, f, indent=4)

if __name__ == "__main__":
    asyncio.run(main())