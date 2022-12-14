'''
This script collects the top 1000 Uniswap V2 tokens ordered descending by tradeVolumeUSD, it is not used in the final product but is handy for testing.
'''

# standard library imports
import asyncio
# local imports
from pool_collector import get_pool_permutations

async def main():
    # query for USDC and WETH
    tokens = ['USDC', 'WETH']
    # get the top 100 pools
    X = 100
    tokenB = 'USDC'
    ID_B = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    tokenA = 'WETH'
    ID_A = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    # get the pools
    pools = await get_pool_permutations(tokenA, ID_A, tokenB, ID_B, X) 

if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # only need this if running on windows
    asyncio.run(main())