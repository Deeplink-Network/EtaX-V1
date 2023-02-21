# local imports
from smart_order_router import route_orders, refresh_pools
from threading import Thread
from multiprocessing import Process

# third party imports
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio

app = Flask(__name__)
CORS(app)

DEX_ENDPOINTS = (
    'uniswap-v2',
    'sushiswap-v2'
    )

# create the event loop
loop = asyncio.get_event_loop()

@app.route('/order_router', methods=['GET'])
async def order_router():
    print('ORDER ROUTER CALLED')
    # get the input parameters from the request
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    buy_symbol = str(request.args.get('buy_symbol'))
    buy_ID = str(request.args.get('buy_ID'))

    # run the route_orders coroutine
    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID)
    
    # return the result to the client
    return jsonify(result)

@app.route('/refresh_pools', methods=['GET'])
async def refresh_pools_async(dex):
    if dex == 'uniswap-v2':
        await refresh_pools('Uniswap V2')
    elif dex == 'sushiswap-v2':
        await refresh_pools('SushiSwap V2')

async def refresh_task():
    while True:
        tasks = [asyncio.create_task(refresh_pools_async(dex)) for dex in DEX_ENDPOINTS]
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)

def start_refresh_task():
    # start the refresh task
    asyncio.run(refresh_task())

def main():
    # start the refresh task in a separate thread
    refresh_thread = Thread(target=start_refresh_task)
    refresh_thread.start()
    # start the Flask app
    app.run()

if __name__ == '__main__':
    asyncio.run(main()) 