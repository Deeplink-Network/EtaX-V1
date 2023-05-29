'''
This module is used to traverse the paths and calculate the price impact at each swap.
'''

# local imports
from price_impact_calculator import xyk_price_impact, get_max_amount_for_impact_limit, constant_mean_price_impact, dodo_price_impact
from gas_fee_estimator import get_gas_fee_in_eth
# standard library imports
import networkx as nx
# import json
from constants import MAX_ROUTES
import dotenv
import os

'''# load coinmarketcap api key from .env
dotenv.load_dotenv()
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

def get_token_price_usd(symbol, convert_to_symbol="USD"):
    url = f"https://pro-api.coinmarketcap.com/v1/tools/price-conversion?amount=1&symbol={symbol}&convert={convert_to_symbol}"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY
    }
    response = requests.get(url, headers=headers)
    response_data = json.loads(response.text)
    return response_data["data"]["quote"][convert_to_symbol]["price"]'''

G = nx.DiGraph()

# calculate routes
def calculate_routes(G: nx.DiGraph(), paths: list, sell_amount: float, sell_symbol: str, buy_symbol: str) -> dict:
    gas_fee = get_gas_fee_in_eth()
    count = 0
    routes = {}
    for path in paths:
        try:
            swap_number = 0
            for pool in path:
                protocol = G.nodes[pool]['pool']['protocol']
                dangerous = G.nodes[pool]['pool']['dangerous']

                if protocol == 'Balancer_V1' or protocol == 'Balancer_V2':
                    price_impact_function = constant_mean_price_impact
                elif protocol == 'DODO':
                    price_impact_function = dodo_price_impact
                else:
                    price_impact_function = xyk_price_impact

                if pool == path[0]:
                    # get the price impact calculator values
                    values = price_impact_function(
                        G.nodes[pool]['pool'], sell_symbol, sell_amount)

                    output_symbol = values['buy_symbol']
                    output_amount = values['actual_return']
                    price_impact = values['price_impact']
                    description = values['description']

                    # determine whether output_symbol is token0 or token1
                    output_token_num = 0
                    if output_symbol == G.nodes[pool]['pool']['token1']['symbol']:
                        output_token_num = 1

                    # add the route to the dictionary under the swap key
                    output_amount_zero = output_amount == 0

                    routes[f'route_{count}'] = {
                        f'swap_{swap_number}': {
                            'pool': pool,
                            'exchange': protocol,
                            'dangerous': dangerous,
                            'input_token': sell_symbol,
                            'input_amount': sell_amount,
                            'input_amount_usd': sell_amount*float(G.nodes[pool][f'token{output_token_num^1}']['priceUSD']) if not output_amount_zero else 0, # ^1 flips 0 to 1 and 1 to 0
                            'output_token': output_symbol,
                            'output_amount': output_amount,
                            'output_amount_usd': output_amount*float(G.nodes[pool][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else 0,
                            'price_impact': price_impact,
                            'price': sell_amount/output_amount if not output_amount_zero else float('inf'),
                            'price_usd': sell_amount*float(G.nodes[pool][f'token{output_token_num^1}']['priceUSD'])/output_amount*float(G.nodes[pool][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else float('inf'),
                            'gas_fee': gas_fee,
                            'description': description
                        }
                    }

                    swap_number += 1

                else:
                    input_amount = output_amount
                    old_input_symbol = output_symbol
                    values = price_impact_function(
                        G.nodes[pool]['pool'], output_symbol, output_amount)
                    
                    output_symbol = values['buy_symbol']
                    output_amount = values['actual_return']
                    price_impact = values['price_impact']
                    description = values['description']

                    # determine whether output_symbol is token0 or token1
                    output_token_num = 0
                    if output_symbol == G.nodes[pool]['pool']['token1']['symbol']:
                        output_token_num = 1

                    output_amount_zero = output_amount == 0

                    # add the route to the dictionary under the swap key
                    routes[f'route_{count}'][f'swap_{swap_number}'] = {
                        'pool': pool,
                        'exchange': protocol,
                        'dangerous': dangerous,
                        'input_token': old_input_symbol,
                        'input_amount': input_amount,
                        'input_amount_usd': input_amount*float(G.nodes[pool][f'token{output_token_num^1}']['priceUSD']) if not output_amount_zero else 0, # ^1 flips 0 to 1 and 1 to 0
                        'output_token': output_symbol,
                        'output_amount': output_amount,
                        'output_amount_usd': output_amount*float(G.nodes[pool][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else 0,
                        'price_impact': price_impact,
                        'price': input_amount/output_amount if not output_amount_zero else float('inf'),
                        'price_usd': input_amount*float(G.nodes[pool][f'token{output_token_num^1}']['priceUSD'])/output_amount*float(G.nodes[pool][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else float('inf'),
                        'gas_fee': gas_fee,
                        'description': description
                    }

                    swap_number += 1      

            else:
                output_amount_zero = output_amount == 0
                # add the final price, total gas fee, and path to the dictionary
                routes[f'route_{count}']['amount_in'] = sell_amount
                routes[f'route_{count}']['amount_in_usd'] = sell_amount*float(G.nodes[path[0]]['pool'][f'token{output_token_num^1}']['priceUSD']) if not output_amount_zero else None
                routes[f'route_{count}']['amount_out'] = output_amount
                routes[f'route_{count}']['amount_out_usd'] = output_amount*float(G.nodes[path[-1]]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else None

            routes[f'route_{count}']['price'] = sell_amount/output_amount if not output_amount_zero else float('inf')
            routes[f'route_{count}']['price_usd'] = sell_amount*float(G.nodes[path[0]]['pool'][f'token{output_token_num^1}']['priceUSD'])/output_amount*float(G.nodes[path[-1]]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else float('inf')
            routes[f'route_{count}']['gas_fee'] = gas_fee*swap_number
            routes[f'route_{count}']['path'] = path
            routes[f'route_{count}']['price_impact'] = sum(
                [routes[f'route_{count}'][f'swap_{i}']['price_impact'] for i in range(swap_number)])
            count += 1

            # print('------------------------------------------------------------')

        except Exception as e:
            # redundant error check, delete the route if it doesn't work
            if f'route_{count}' in routes:
                del routes[f'route_{count}']
            print(e)
            continue

        # sort routes by amount out
    routes = sorted(
        routes.items(), key=lambda item: item[1]['amount_out'], reverse=True)
    return routes


def get_sub_route(g, path: dict, new_sell_amount: float, sell_symbol: str, p: float, gas_fee: float):
    route = {'percent': p}
    swap_no = 0
    for pool in path:
        protocol = g.nodes[pool]['pool']['protocol']
        dangerous = g.nodes[pool]['pool']['dangerous']

        if protocol == 'Balancer_V1' or protocol == 'Balancer_V2':
            price_impact_function = constant_mean_price_impact
        elif protocol == 'DODO':
            price_impact_function = dodo_price_impact
        else:
            price_impact_function = xyk_price_impact

        if pool == path[0]:
            # get the price impact calculator values
            values = price_impact_function(
                g.nodes[pool]['pool'], sell_symbol, new_sell_amount)

            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']

            # determine whether output_symbol is token0 or token1
            output_token_num = 0
            if output_symbol == g.nodes[pool]['pool']['token1']['symbol']:
                output_token_num = 1

            output_amount_zero = output_amount == 0

            # add the route to the dictionary under the swap key
            route[f'swap_{swap_no}'] = {
                'pool': pool,
                'exchange': protocol,
                'dangerous': dangerous,
                'input_token': sell_symbol,
                'input_amount': new_sell_amount,
                'input_amount_usd': new_sell_amount*float(g.nodes[pool]['pool'][f'token{output_token_num^1}']['priceUSD']) if not output_amount_zero else 0, # ^1 flips 0 to 1 and 1 to 0
                'output_token': output_symbol,
                'output_amount': output_amount,
                'output_amount_usd': output_amount*float(g.nodes[pool]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else 0,
                'price_impact': price_impact,
                'price': new_sell_amount/output_amount if not output_amount_zero else float('inf'),
                'price_usd': new_sell_amount*float(g.nodes[pool]['pool'][f'token{output_token_num^1}']['priceUSD'])/output_amount*float(g.nodes[pool]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else float('inf'),
                'gas_fee': gas_fee,
                'description': description,
            }

        else:
            input_amount = output_amount
            old_input_symbol = output_symbol
            values = price_impact_function(
                g.nodes[pool]['pool'], output_symbol, output_amount)

            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']

            # determine whether output_symbol is token0 or token1
            output_token_num = 0
            if output_symbol == g.nodes[pool]['pool']['token1']['symbol']:
                output_token_num = 1

            output_amount_zero = output_amount == 0

            # add the route to the dictionary under the swap key
            route[f'swap_{swap_no}'] = {
                'pool': pool,
                'exchange': protocol,
                'dangerous': dangerous,
                'input_token': old_input_symbol,
                'input_amount': input_amount,
                'input_amount_usd': input_amount*float(g.nodes[pool]['pool'][f'token{output_token_num^1}']['priceUSD']) if not output_amount_zero else 0, # ^1 flips 0 to 1 and 1 to 0
                'output_token': output_symbol,
                'output_amount': output_amount,
                'output_amount_usd': output_amount*float(g.nodes[pool]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else 0,
                'price_impact': price_impact,
                'price': input_amount/output_amount if not output_amount_zero else float('inf'),
                'price_usd': input_amount*float(g.nodes[pool]['pool'][f'token{output_token_num^1}']['priceUSD'])/output_amount*float(g.nodes[pool]['pool'][f'token{output_token_num}']['priceUSD']) if not output_amount_zero else float('inf'),
                'gas_fee': gas_fee,
                'description': description,
                'percent': p
            }


        swap_no += 1
    return route


def get_final_route(g, routes: dict, sell_amount: float, sell_symbol: str) -> list:
    """Given a list of valid routes, sorted by amount out, get a final path which may split the order into multiple paths."""
    final_route = {'paths': []}
    remaining = sell_amount
    gas_fee = get_gas_fee_in_eth()
    route_num = 0
    for _, route in routes:
        # get the max amount that can be swapped without exceeding the price impact limit
        first_pool_id = route['swap_0']['pool']
        second_pool_id = route['swap_1']['pool'] if 'swap_1' in route else 0
        first_pool = g.nodes[first_pool_id]['pool']

        max_amount = min(get_max_amount_for_impact_limit(g, route), remaining)
        p = (max_amount / sell_amount) * 100
        if p < 1:
            continue
        # add the route to the final path
        final_route['paths'].append(get_sub_route(
            g, route['path'], max_amount, sell_symbol, p, gas_fee))
        route_num += 1
        if route_num == MAX_ROUTES:
            break
        # subtract the max amount from the remaining amount
        remaining -= max_amount
        # if the remaining amount is less than 0.01, stop
        if remaining < 0.01:
            break

    routes = final_route['paths']
    final_route['output_amount'] = sum(
        [route[f'swap_{len(route)-2}']['output_amount'] for route in routes])
    final_route['gas_fee'] = sum(
        [route[f'swap_{len(route)-2}']['gas_fee'] for route in routes])
    
    # handles cases where output amount approaches 0
    try:
        final_route['price'] = sell_amount/final_route['output_amount']
    except ZeroDivisionError:
        k = 1e-9  # arbitrarily small number, not too close to 0
        final_route['price'] = sell_amount / (final_route['output_amount'] + k)

    final_route['price_impact'] = sum(
        [route[f'swap_{len(route)-2}']['price_impact'] for route in routes]) / (len(final_route) - 3)
    return final_route
