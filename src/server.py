'''
This file contains the code for the Flask server that will be used to route orders.
'''

# local imports
from smart_order_router import route_orders, refresh_pools
from threading import Thread
from multiprocessing import Process

# third party imports
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from asyncio import Queue
import requests
import time

app = Flask(__name__)
CORS(app)

# define the maximum number of concurrent requests
MAX_CONCURRENT_REQUESTS = 10

# create a queue to store the incoming requests
# request_queue = Queue(maxsize=MAX_CONCURRENT_REQUESTS)
# create the event loop
loop = asyncio.get_event_loop()
    

'''
INPUTS:
- sell_symbol: the symbol of the token to sell, string, e.g. 'USDC'
- sell_ID: the ID of the token to sell, string, e.g. '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
- sell_amount: the amount of the token to sell, float, e.g. 100000
- buy_symbol: the symbol of the token to buy, string, e.g. 'WETH'
- buy_ID: the ID of the token to buy, string, e.g. '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

OUTPUTS:
result: a dictionary containing the pool graph, path graph, and routes
- pool_graph: a dictionary of lists mapping each node to its neighbors
- path_graph: a dictionary of lists mapping each node to its neighbors
- routes: a dictionary of routes, each route contains the input amount, output amount, price, gas fee, and the nodes in the route
    - each route also has a key for each swap in the route, each swap contains:
    - the pool, input token, input amount, output token, output amount, price impact, price, gas fee, and description

see example.ipynb for example outputs, or swagger.yaml for the structure of the output

sample queries (when running locally):
100,000 USDC for WETH
http://localhost:5000/order_router?sell_symbol=WETH&sell_ID=0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2&sell_amount=100000&buy_symbol=USDC&buy_ID=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48

50,000 DAI for LINK
http://localhost:5000/order_router?sell_symbol=DAI&sell_ID=0x6b175474e89094c44da98b954eedeac495271d0f&sell_amount=50000&buy_symbol=LINK&buy_ID=0x514910771af9ca656af840dff83e8264ecf986ca

250,000 FTM for AGIX
http://localhost:5000/order_router?sell_symbol=FTM&sell_ID=0x4e15361fd6b4bb609fa63c81a2be19d873717870&sell_amount=250000&buy_symbol=AGIX&buy_ID=0x5b7533812759b45c2b44c19e320ba2cd2681b542
'''
@app.route('/order_router', methods=['GET'])
async def order_router():
    # get the input parameters from the request
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    buy_symbol = str(request.args.get('buy_symbol'))
    buy_ID = str(request.args.get('buy_ID'))

    # create a task to run the coroutine
    # task = asyncio.create_task(route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID))
    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID)
    # add the task to the queue
    #await request_queue.put(task)

    # wait for the task to complete
    
    # return the result to the client
    return jsonify(result)

@app.route('/refresh_pools', methods=['GET'])
async def refresh_pools_req():
    await refresh_pools()
    return 'OK'

def query_refresh():
    time.sleep(5)
    requests.get('http://localhost:5000/refresh_pools')

async def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def refresh_task():
    while True:
        await refresh_pools()
        await asyncio.sleep(30)

async def main():
    process = Process(target=query_refresh)
    process.start()
    app.run()

# run the Flask app
if __name__ == '__main__':
    asyncio.run(main())