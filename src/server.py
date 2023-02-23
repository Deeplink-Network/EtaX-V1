from smart_order_router import route_orders, refresh_pools, DEX_LIST
from threading import Thread
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio

app = Flask(__name__)
CORS(app)

loop = asyncio.get_event_loop()


async def refresh_all_pools():
    while True:
        refresh_tasks = [refresh_pools(dex) for dex in DEX_LIST]
        await asyncio.gather(*refresh_tasks)
        await asyncio.sleep(30)


@app.route('/order_router_split', methods=['GET'])
async def order_router_split():
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    buy_symbol = str(request.args.get('buy_symbol'))
    buy_ID = str(request.args.get('buy_ID'))
    exchanges = request.args.get('exchanges', DEX_LIST)

    print('ORDER ROUTER CALLED')

    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID, exchanges, split=True)

    return jsonify(result)

@app.route('/order_router', methods=['GET'])
async def order_router():
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    buy_symbol = str(request.args.get('buy_symbol'))
    buy_ID = str(request.args.get('buy_ID'))
    exchanges = request.args.get('exchanges', DEX_LIST)

    print('ORDER ROUTER CALLED')

    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID, exchanges, split=False)

    return jsonify(result)

async def main():
    refresh_task = asyncio.create_task(refresh_all_pools())

    threads = [
        Thread(target=app.run)
    ]

    for thread in threads:
        thread.start()

    await refresh_task

if __name__ == '__main__':
    loop.run_until_complete(main())
