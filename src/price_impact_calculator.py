'''
This script calculates the price impact of a swap in a given pool using the xyk constant product formula.
'''

# calculate the predicted price impact percentage when swapping one token for another in a given pool
def xyk_price_impact(pool: dict, sell_symbol: str, sell_amount: str) -> dict:
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
    k = x*y
    
    # calculate new amount of buy_token in the pool after xyk adjustment
    y_new = k/(x+sell_amount)
    
    # calculate actual amount of buy_token received
    actual_return = y-y_new
    
    # calculate price impact percentage
    price_impact = (1-(actual_return/expected_return))*100

    description = f"""Sell {sell_amount} {sell_symbol} for {pool[f'token{buy_token}']['symbol']} in {pool['protocol']} {pool['id']}
    \nExpected payout: {expected_return} {pool[f'token{buy_token}']['symbol']}
    \nActual payout: {actual_return} {pool[f'token{buy_token}']['symbol']}
    \nPrice impact: {price_impact}%
    """
    
    # actual return: the amount of buy_token received, price impact: the percentage of price impact, buy_symbol: the symbol of the buy token, description: a description of the swap
    return {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}