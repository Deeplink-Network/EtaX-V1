'''
This script calculates the price impact of a swap in a given pool using the xyk constant product formula.
'''
# Max price impact for a path before the order is split
import json
from constants import SUSHISWAP_V2, BALANCER_V1, UNISWAP_V2
MAX_PRICE_IMPACT = 0.10

# calculate the predicted price impact percentage when swapping one token for another in a given XYK pool
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

    # constant product formula (xyk)
    x = float(pool[f'reserve{sell_token}'])
    y = float(pool[f'reserve{buy_token}'])

    # Sushiswap subgraph returns decimals adjusted values, so we need to adjust them back
    if pool['protocol'] == SUSHISWAP_V2:
        x = x/10**int(pool[f'token{sell_token}']['decimals'])
        y = y/10**int(pool[f'token{buy_token}']['decimals'])

    print(x, y)

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

# price function, useful for max price impact calculation
def constant_mean_spot_price(pool: dict, sell_token: str, buy_token: str) -> float:
    """Calculates the spot price for constant mean AMM tokens given the token balances, token weights, and swap fee."""
    # Get the balances of the tokens
    token_balance_in = float(pool['reserve'+str(sell_token)])
    token_balance_out = float(pool['reserve'+str(buy_token)])

    # Get the weights of the tokens
    token_weight_in = float(pool['token'+str(sell_token)]['denormWeight'])
    token_weight_out = float(pool['token'+str(buy_token)]['denormWeight'])

    # Get the swapFee
    swap_fee = float(pool['swapFee'])

    numer = float(token_balance_in) / float(token_weight_in)
    denom = float(token_balance_out) / float(token_weight_out)
    ratio = numer / denom
    scale = 1 / (1 - float(swap_fee))

    return ratio * scale

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

    ret = {'actual_return': token_amount_out, 'price_impact': price_impact_percentage, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}

    print(ret)
    
    return ret


def get_max_amount_for_impact_limit(g, path: dict):
    """Returns the maximum amount of sell token that can be swapped in the path without exceeding the max price impact limit.

    Starts at the end pool and calculates the amount of sell token that can be swapped without exceeding the max price impact limit. Then moves back to the start, finding how much of the sell token is needed to swap the amount calculated in the previous pool, as well as the amount of the token in that pool required to not break the price impact limit. The minimum of these two values is taken. This is repeated until the start pool is reached.
    """

    pool_num = len(path)-6
    sell_amount = None
    max_price_imp_amount = None
    next_pool_amount = 10e30

    print(json.dumps(path, indent=4))

    while pool_num >= 0:

        swap = path[f'swap_{pool_num}']
        pool = g.nodes[swap['pool']]['pool']

        print(pool)

        sell_token = swap['input_token']
        buy_token = swap['output_token']

        sell_token_num = 1 if pool['token1']['symbol'] == sell_token else 0
        buy_token_num = 1 - sell_token_num

        # grab the expected price of the asset being purchased
        if pool['protocol'] == BALANCER_V1:
            expected_price = constant_mean_spot_price(pool, sell_token, sell_amount)
        else:
            expected_price = float(pool[f'token{sell_token_num}Price'])

        # constant product formula (xyk)
        x = float(pool[f'reserve{sell_token_num}'])
        y = float(pool[f'reserve{buy_token_num}'])

        # Sushiswap subgraph returns decimals adjusted values, so we need to adjust them back
        if pool['protocol'] == SUSHISWAP_V2:
            x = x/10**int(pool[f'token{sell_token_num}']['decimals'])
            y = y/10**int(pool[f'token{buy_token_num}']['decimals'])

        if max_price_imp_amount:
            next_pool_amount = max_price_imp_amount * expected_price
            print(
                f'next_pool_amount: {next_pool_amount}, based on max_price_imp_amount: {max_price_imp_amount} and expected_price: {expected_price}')
        # mp = MAX_PRICE_IMPACT, ep = expected_price, sa = sell_amount

        # actual_return / expected_return should equal 1 - MAX_PRICE_IMPACT

        # => y - y_new = (1 - MAX_PRICE_IMPACT) * expected_return
        # = (1 - MAX_PRICE_IMPACT) * (sell_amount / expected_price)
        # => y - k / (x + sa) = (1 - mp) * sa / ep

        # => k / (x + sa) = y - (1 - mp) * (sa / ep)
        # => k = yx + y.sa - (1 - mp) * (sa / ep) * (x + sa)
        # k cancels out, set MP = (1 - mp)
        # => y.sa - MP(sa.x + sa^2) / ep = 0
        # => sa^2 + (x - y.ep/MP)sa = 0
        # => sa(sa + (x - y.ep/MP)) = 0
        # sa = -(x - y.ep/MP)

        max_price_imp_amount = - \
            (x - (y * expected_price) / (1 - MAX_PRICE_IMPACT))
        sell_amount = min(max_price_imp_amount, next_pool_amount)
        print(sell_amount)
        pool_num -= 1
    return sell_amount
