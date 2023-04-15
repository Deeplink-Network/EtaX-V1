'''
This script calculates the price impact of a swap in a given pool using the xyk constant product formula.
'''
# Max price impact for a path before the order is split
# import json
from constants import SUSHISWAP_V2, UNISWAP_V2, CURVE
import logging

MAX_PRICE_IMPACT = 0.10

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
    token_weight_in = float(pool['token'+str(sell_token)]['denormWeight'])
    token_weight_out = float(pool['token'+str(buy_token)]['denormWeight'])

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
    pool_num = len(path) - 7
    sell_amount = None
    next_pool_amount = 10e30

    while pool_num >= 0:
        swap = path[f'swap_{pool_num}']
        pool = g.nodes[swap['pool']]['pool']
        sell_symbol = swap['input_token']

        if pool['protocol'] == 'Balancer_V1':
            price_impact_function = constant_mean_price_impact
        else:
            price_impact_function = xyk_price_impact

        # Check whether sell token is token0 or token1
        token = 1
        if pool['token0']['symbol'] == sell_symbol:
            token = 0

        left = 0
        right = float(pool[f'reserve{token}'])  # Start with the entire pool's balance as the upper limit
        epsilon = 1e-6  # Tolerance level for binary search

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