'''
This script calculates the price impact of a swap in a given pool using the xyk constant product formula.
'''
# Max price impact for a path before the order is split
import json
from constants import SUSHISWAP_V2, UNISWAP_V2, CURVE, BALANCER_V1, BALANCER_V2, DODO
import logging
import os
from web3 import Web3
import requests
import numpy as np

MAX_PRICE_IMPACT = 50

KEEPER_ADDRESS = Web3.to_checksum_address('0x6c51B510C83288831aDfdC4B76F461d41b45ad07')

# grab keys from environment variables
INFURA_KEY = os.getenv("ETAX_INFURA_KEY", default=None)
INFURA_SECRET = os.getenv("ETAX_INFURA_SECRET", default=None)
# strip the quotes from the infura key if they exist
INFURA_KEY = INFURA_KEY.strip('"') if INFURA_KEY else None
INFURA_SECRET = INFURA_SECRET.strip('"') if INFURA_SECRET else None

NODE_URL = 'https://mainnet.infura.io/v3/{}'.format(INFURA_KEY)
w3 = Web3(Web3.HTTPProvider(NODE_URL))

# this is a placeholder web3-based price impact retrieval method, 
# it will be replaced with a mathematical implementation 
def dodo_price_impact(pool: dict, sell_symbol: str, sell_amount: float) -> dict:
    print('Calculating price impact for DODO pool: '+pool['id'])
    # check that the sell token is accepted by the pool
    if sell_symbol not in [pool['token0']['symbol'], pool['token1']['symbol']]:
        print('Sell token not accepted by pool: '+pool['id'])
        return pool['id']

    # open the ABI corresponding to the pool type
    with open(f'ABI/DODO_{pool["type"]}.json', 'r') as f:
        ABI = json.load(f)

    contract_address = Web3.to_checksum_address(pool['id'])

    # create a contract object
    contract = w3.eth.contract(address=contract_address, abi=ABI)

    sell_token = 0
    buy_token = 1
    # check which token is the one you are trying to sell
    # swap sell,buy token if not 0,1
    if pool['token1']['symbol'] == sell_symbol:
        sell_token = 1
        buy_token = 0

    try:
        if pool['type'] == 'CLASSICAL' and sell_token == 0:
            # querySellBaseToken
            # print(f'querySellBaseToken({int(sell_amount*10**float(pool[f"token{sell_token}"]["decimals"]))})')
            tokens_received = contract.functions.querySellBaseToken(
                    int(sell_amount*10**float(pool[f'token{sell_token}']['decimals']))).call()

        elif pool['type'] == 'CLASSICAL' and sell_token == 1:
            # querySellQuoteToken
            # print(f'querySellQuoteToken({int(sell_amount*10**float(pool[f"token{sell_token}"]["decimals"]))})')
            tokens_received = contract.functions.queryBuyBaseToken(
                int(sell_amount*10**float(pool[f'token{sell_token}']['decimals']))).call()

        elif pool['type'] != 'CLASSICAL' and sell_token == 0:
            # print(f'querySellBase({KEEPER_ADDRESS}, {int(sell_amount*10**float(pool[f"token{sell_token}"]["decimals"]))})')
            # querySellBase
            tokens_received = contract.functions.querySellBase(
                KEEPER_ADDRESS,
                int(sell_amount*10**float(pool[f'token{sell_token}']['decimals']))).call()

        elif pool['type'] != 'CLASSICAL' and sell_token == 1:
            # print(f'querySellQuote({KEEPER_ADDRESS}, {int(sell_amount*10**float(pool[f"token{sell_token}"]["decimals"]))})')
            # querySellQuote
            tokens_received = contract.functions.querySellQuote(
                KEEPER_ADDRESS,
                int(sell_amount*10**float(pool[f'token{sell_token}']['decimals']))).call()

        if pool['type'] == 'CLASSICAL':
            tokens_received = tokens_received / 10**float(pool[f'token{buy_token}']['decimals'])
        else:
            tokens_received = tokens_received[0] / 10**float(pool[f'token{buy_token}']['decimals'])

        # calculate price impact as a percentage
        initial_price = float(pool['token1Price']) if sell_symbol == pool['token0']['symbol'] else float(pool['token0Price'])
        expected_return = sell_amount/initial_price
        actual_return = tokens_received
        price_impact = max(0, (1-(actual_return/expected_return))*100)

        ret = {
            'actual_return': tokens_received,
            'price_impact': price_impact,
            'buy_symbol': pool[f'token{buy_token}']['symbol'],
            'description': f"Sell {sell_amount} {sell_symbol} for {pool[f'token{buy_token}']['symbol']} in DODO {pool['id']}\n"
                        f"Expected return: {tokens_received} {pool[f'token{buy_token}']['symbol']}\n"
                        f"Price impact: {price_impact}%"
        }
        print()
        return ret


    except Exception as e:
        print(f'ValueError {e}: {pool["id"]}')
        ret = {
            'actual_return': 0,
            'price_impact': np.inf,
            'buy_symbol': pool[f'token{buy_token}']['symbol'],
            'description': f"pool {pool['id']} is not active"
        }
        print()
        return ret


# calculate the predicted price impact percentage when swapping one token for another in a given pool
def xyk_price_impact(pool: dict, sell_symbol: str, sell_amount: float) -> dict:
    # NOR check that sell_token is in the pool, do not proceed if it is not
    if sell_symbol not in [pool['token0']['symbol'], pool['token1']['symbol']]:
        print('Sell token not accepted by pool: '+pool['id'])
        return pool['id']

    sell_token = 0
    buy_token = 1
    # check which token is the one you are trying to sell
    # swap sell,buy token if not 0,1
    if pool['token1']['symbol'] == sell_symbol:
        sell_token = 1
        buy_token = 0

    # grab the expected price of the asset being purchased
    expected_price = float(pool[f'token{sell_token}Price'])
    # calculated the expected return
    expected_return = sell_amount/expected_price

    if pool['protocol'] == CURVE:
        actual_return = min(float(pool[f'reserve{buy_token}']), expected_return)
        price_impact = (1-(actual_return/expected_return))*100
        if actual_return == 0:
            logging.error('Curve pool has no liquidity: '+pool['id'])

    else:
        # constant product formula (xyk)
        x = float(pool[f'reserve{sell_token}'])
        y = float(pool[f'reserve{buy_token}'])

        # Sushiswap subgraph returns decimals adjusted values, so we need to adjust them back
        if pool['protocol'] == SUSHISWAP_V2:
            x = x/10**int(pool[f'token{sell_token}']['decimals'])
            y = y/10**int(pool[f'token{buy_token}']['decimals'])

        # print(x, y)

        k = x*y

        # calculate new amount of buy_token in the pool after xyk adjustment
        y_new = k/(x+sell_amount)

        # calculate actual amount of buy_token received
        actual_return = y-y_new

        # calculate price impact percentage
        price_impact = (1-(actual_return/expected_return))*100

    description = f"""Sell {sell_amount} {sell_symbol} for {pool[f'token{buy_token}']['symbol']} in {' '.join(pool['protocol'].split('_'))} {pool['id']}
    \nExpected return: {actual_return} {pool[f'token{buy_token}']['symbol']}
    \nPrice impact: {price_impact}%
    """

    # actual return: the amount of buy_token received, price impact: the percentage of price impact, buy_symbol: the symbol of the buy token, description: a description of the swap
    return {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}


def constant_mean_price_impact(pool: dict, sell_symbol: str, sell_amount: float) -> dict:
    """ Calculates the price impact for a given trade in a balancer pool. """

    # NOR check that sell_token is in the pool, do not proceed if it is not
    if sell_symbol not in [pool['token0']['symbol'], pool['token1']['symbol']]:
        print('Sell token not accepted by pool: '+pool['id'])
        return pool['id']

    # set the token numbers for the pool
    sell_token = 0
    buy_token = 1
    # check which token is the one you are trying to sell
    # swap sell,buy token if not 0,1
    if pool['token1']['symbol'] == sell_symbol:
        sell_token = 1
        buy_token = 0

    # Get the balances of the tokens
    token_balance_in = float(pool['reserve'+str(sell_token)])
    token_balance_out = float(pool['reserve'+str(buy_token)])

    # Get the weights of the tokens
    if pool['protocol'] == BALANCER_V1:
        token_weight_in = float(pool['token'+str(sell_token)]['denormWeight'])
        token_weight_out = float(pool['token'+str(buy_token)]['denormWeight'])
    elif pool['protocol'] == BALANCER_V2:
        token_weight_in = float(pool['token'+str(sell_token)]['weight'])
        token_weight_out = float(pool['token'+str(buy_token)]['weight'])
        
    # Get the swapFee
    swap_fee = float(pool['swapFee'])

    # Calculate the spot price before the swap
    numer = float(token_balance_in) / float(token_weight_in)
    denom = float(token_balance_out) / float(token_weight_out)
    price_before = numer / denom * (1 / (1 - float(swap_fee)))

    # Calculate the ratio of the weights
    weight_ratio = token_weight_in / token_weight_out

    # Apply the swap fee to the input token amount
    adjusted_in = sell_amount * (1 - swap_fee)

    # Calculate the relative amount of the input token in the pool
    input_token_ratio = token_balance_in / (token_balance_in + adjusted_in)

    # Calculate the output token amount based on the pool balance and the input token ratio
    output_token_ratio = 1 - pow(input_token_ratio, weight_ratio)
    token_amount_out = token_balance_out * output_token_ratio

    # Calculate the amount of input tokens that were actually used (after the swap fee)
    actual_input_amount = sell_amount - adjusted_in

    # Calculate the updated pool balances after the swap
    input_balance = token_balance_in + actual_input_amount
    output_balance = token_balance_out - token_amount_out
    
    # Calculate the spot price after the swap
    price_after = (input_balance / token_weight_in) / (output_balance / token_weight_out) * (1 / (1 - float(swap_fee)))

    # Calculate the price impact as a percentage
    price_impact_percentage = (price_after - price_before) / price_before * 100

    description = f"""Sell {sell_amount} {sell_symbol} for {pool[f'token{buy_token}']['symbol']} in {' '.join(pool['protocol'].split('_'))} {pool['id']}
    \nExpected return: {token_amount_out} {pool[f'token{buy_token}']['symbol']}
    \nPrice impact: {price_impact_percentage}%
    """

    return {'actual_return': token_amount_out, 'price_impact': price_impact_percentage, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}


def get_max_amount_for_impact_limit(g, path: dict) -> float:
    pool_num = sum(key.startswith('swap_') for key in path) - 1 # more consistent than len(path) - X, need to remember not to add any keys that start with swap_
    print(f'pool_num: {pool_num}')
    print('path:')
    print(path)
    sell_amount = None
    next_pool_amount = 10e30

    while pool_num >= 0:
        swap = path[f'swap_{pool_num}']
        print(swap)
        pool = g.nodes[swap['pool']]['pool']
        sell_symbol = swap['input_token']
        buy_symbol = swap['output_token']

        if pool['protocol'] == BALANCER_V1 or pool['protocol'] == BALANCER_V2:
            price_impact_function = constant_mean_price_impact
        elif pool['protocol'] == DODO:
            price_impact_function = dodo_price_impact
        else:
            price_impact_function = xyk_price_impact

        # Check whether sell token is token0 or token1
        token = 1
        if pool['token0']['symbol'] == sell_symbol:
            token = 0

        left = 0
        right = float(pool[f'reserve{token}']) * 10  # Start with the entire pool's balance as the upper limit

        # Tolerance level for binary search
        if pool['protocol'] == DODO:
            epsilon = 5
        else:
            epsilon = 1e-6  


        while right - left > epsilon:
            mid = (left + right) / 2
            price_impact_data = price_impact_function(pool, sell_symbol, mid)
            price_impact = price_impact_data['price_impact']

            if price_impact < MAX_PRICE_IMPACT:
                left = mid
            else:
                right = mid

        max_amount = left
        if sell_amount is not None:
            max_amount = min(max_amount, next_pool_amount)

        next_pool_amount = max_amount
        sell_amount = max_amount

        pool_num -= 1

    return sell_amount