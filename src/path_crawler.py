'''
This module is used to traverse the paths and calculate the price impact at each swap.
'''

# local imports
from price_impact_calculator import xyk_price_impact, get_max_amount_for_impact_limit
from gas_fee_estimator import get_gas_fee_in_eth
# standard library imports
import networkx as nx
import json

G = nx.DiGraph()

# calculate routes 
def calculate_routes(G: nx.DiGraph(), paths: list, sell_amount: float, sell_symbol: str, buy_symbol: str) -> dict:
    gas_fee = get_gas_fee_in_eth()
    count = 0
    routes = {}
    for path in paths:
        print(f'path {count}')
        try:
            swap_number = 0
            for pool in path:
                print(pool)
                print(f'swap {swap_number}')
                if pool == path[0]:
                    # get the price impact calculator values
                    values = xyk_price_impact(G.nodes[pool]['pool'], sell_symbol, sell_amount)
                    # {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}
                    output_symbol = values['buy_symbol']
                    output_amount = values['actual_return']
                    price_impact = values['price_impact']
                    description = values['description']
                    print(description)

                    # add the route to the dictionary under the swap key
                    routes[f'route_{count}'] = {
                        f'swap_{swap_number}': {
                            'pool': pool,
                            'input_token': sell_symbol,
                            'input_amount': sell_amount,
                            'output_token': output_symbol,
                            'output_amount': output_amount,
                            'price_impact': price_impact,
                            'price': sell_amount/output_amount,
                            'gas_fee': gas_fee,
                            'description': description
                        }
                    }
                    swap_number += 1

                else:
                    input_amount = output_amount
                    values = xyk_price_impact(G.nodes[pool]['pool'], output_symbol, output_amount)
                    # {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}
                    output_symbol = values['buy_symbol']
                    output_amount = values['actual_return']
                    price_impact = values['price_impact']
                    description = values['description']
                    print(description)

                    # add the route to the dictionary under the swap key
                    routes[f'route_{count}'][f'swap_{swap_number}'] = {
                        'pool': pool,
                        'input_token': output_symbol,
                        'input_amount': input_amount,
                        'output_token': output_symbol,
                        'output_amount': output_amount,
                        'price_impact': price_impact,
                        'price': input_amount/output_amount,
                        'gas_fee': gas_fee,
                        'description': description
                    }
                    swap_number += 1
                
            else:
                # add the final price, total gas fee, and path to the dictionary
                routes[f'route_{count}']['amount_in'] = sell_amount
                routes[f'route_{count}']['amount_out'] = output_amount
                
            routes[f'route_{count}']['price'] = sell_amount/output_amount
            routes[f'route_{count}']['gas_fee'] = gas_fee*swap_number
            routes[f'route_{count}']['path'] = path
            count += 1
            print('------------------------------------------------------------')
        except:
            # delete the route if it doesn't work
            # del routes[f'route_{count}']
            continue 
        
    # sort routes by amount out
    routes = sorted(routes.items(), key=lambda item: item[1]['amount_out'], reverse=True)
    return routes

def get_sub_route(g, path: dict, new_sell_amount: float, sell_symbol: str, p: float, gas_fee: float):
    route = {'percent': p}
    swap_no = 0
    for pool in path:
        if pool == path[0]:
            # get the price impact calculator values
            values = xyk_price_impact(g.nodes[pool]['pool'], sell_symbol, new_sell_amount)
            # {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}
            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']
            print(description)

            # add the route to the dictionary under the swap key
            route[f'swap_{swap_no}'] = {
                'pool': pool,
                'input_token': sell_symbol,
                'input_amount': new_sell_amount,
                'output_token': output_symbol,
                'output_amount': output_amount,
                'price_impact': price_impact,
                'price': new_sell_amount/output_amount,
                'gas_fee': gas_fee,
                'description': description,
            }
        else:
            input_amount = output_amount
            values = xyk_price_impact(g.nodes[pool]['pool'], output_symbol, output_amount)
            # {'actual_return': actual_return, 'price_impact': price_impact, 'buy_symbol': pool[f'token{buy_token}']['symbol'], 'description': description}
            output_symbol = values['buy_symbol']
            output_amount = values['actual_return']
            price_impact = values['price_impact']
            description = values['description']
            print(description)

            # add the route to the dictionary under the swap key
            route[f'swap_{swap_no}'] = {
                'pool': pool,
                'input_token': output_symbol,
                'input_amount': input_amount,
                'output_token': output_symbol,
                'output_amount': output_amount,
                'price_impact': price_impact,
                'price': input_amount/output_amount,
                'gas_fee': gas_fee,
                'description': description,
                'percent': p
            }

        swap_no += 1
    return route

def get_final_route(g, routes: dict, sell_amount: float, sell_symbol: str) -> list:
    """Given a list of valid routes, sorted by amount out, get a final path which may split the order into multiple paths."""
    final_route = {}
    remaining = sell_amount
    gas_fee = get_gas_fee_in_eth()
    print(g.nodes)
    for i, (_, route) in enumerate(routes):
        # get the max amount that can be swapped without exceeding the price impact limit
        first_pool_id = route['swap_0']['pool']
        print(first_pool_id)
        print(first_pool_id in g.nodes)
        first_pool = g.nodes[first_pool_id]['pool']
        max_amount = min(get_max_amount_for_impact_limit(first_pool, sell_symbol), remaining)
        p = (max_amount / sell_amount) * 100
        # add the route to the final path
        final_route[f'route_{i}'] = get_sub_route(g, route['path'], max_amount, sell_symbol, p, gas_fee)
        # subtract the max amount from the remaining amount
        remaining -= max_amount
        # if the remaining amount is less than 0.01, stop
        if remaining < 0.01:
            break
    print(json.dumps(final_route, indent=4))
    return final_route