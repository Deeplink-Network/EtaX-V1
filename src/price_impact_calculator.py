'''
This script calculates the price impact of a swap in a given pool using the xyk constant product formula.
'''

# Max price impact for a path before the order is split
MAX_PRICE_IMPACT = 0.15

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
    
    # constant product formula (xyk)
    x = float(pool[f'reserve{sell_token}'])
    y = float(pool[f'reserve{buy_token}'])

    # SushiSwap subgraph returns decimals adjusted values, so we need to adjust them back
    if pool['protocol'] == 'SushiSwap V2':
        x = x/10**int(pool[f'token{sell_token}']['decimals'])
        y = y/10**int(pool[f'token{buy_token}']['decimals'])

    k = x*y
    
    # calculate new amount of buy_token in the pool after xyk adjustment
    y_new = k/(x+sell_amount)
    
    # calculate actual amount of buy_token received
    actual_return = y-y_new

    # calculate price impact percentage
    price_impact = (1-(actual_return/expected_return))*100

    description = f"""Sell {sell_amount} {sell_symbol} for {pool[f'token{buy_token}']['symbol']} in {pool['protocol']} {pool['id']}
    \nExpected return: {actual_return} {pool[f'token{buy_token}']['symbol']}
    \nPrice impact: {price_impact}%
    """
    
    # actual return: the amount of buy_token received, price impact: the percentage of price impact, buy_symbol: the symbol of the buy token, description: a description of the swap
    return {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}

def get_max_amount_for_impact_limit(pool: dict, sell_symbol: str):
    """Returns the maximum amount of sell token that can be swapped in a pool without exceeding the max price impact limit"""
    # check that sell_token is in the pool, do not proceed if it is not
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
    expected_return = 1/expected_price
    
    # constant product formula (xyk)
    x = float(pool[f'reserve{sell_token}'])
    y = float(pool[f'reserve{buy_token}'])

    # SushiSwap subgraph returns decimals adjusted values, so we need to adjust them back
    if pool['protocol'] == 'SushiSwap V2':
        x = x/10**int(pool[f'token{sell_token}']['decimals'])
        y = y/10**int(pool[f'token{buy_token}']['decimals'])

    k = x*y

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

    sell_amount = -(x - (y * expected_price) / (1 - MAX_PRICE_IMPACT))
    print(sell_amount)
    return sell_amount

    