'''
This module is used to traverse the paths and calculate the price impact at each swap.
'''

# local imports
from price_impact_calculator import xyk_price_impact
from gas_fee_estimator import get_gas_fee_in_eth
# standard library imports
import networkx as nx

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
            price_impact_over_limit = False  # keep track if any swap has a price impact over 15%
            for pool in path:
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

                    # skip the current route if any swap has a price impact over 15%
                    if price_impact > 15:
                        price_impact_over_limit = True
                        break  

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

                    # skip the current route if any swap has a price impact over 15%
                    if price_impact > 15:
                        price_impact_over_limit = True
                        break  
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

            if price_impact_over_limit:
                # delete the route if any swap has a price impact over 15%
                del routes[f'route_{count}']
                
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