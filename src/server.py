from smart_order_router import route_orders, refresh_pools, DEX_LIST
from threading import Thread
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import asyncio
import time
import requests
from flask_swagger_ui import get_swaggerui_blueprint
from whitenoise import WhiteNoise

app = Flask(__name__)
CORS(app)
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/static/swagger.yaml'  # Our Swagger schema file

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "Smart Order Router"
    }
)

app.register_blueprint(swaggerui_blueprint)

loop = asyncio.get_event_loop()

async def refresh_all_pools():
    refresh_tasks = [refresh_pools(dex) for dex in DEX_LIST]
    try:
        await asyncio.gather(*refresh_tasks)
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        await asyncio.gather(*asyncio.all_tasks())

def pool_thread_task():
    asyncio.run(refresh_all_pools())
    
@app.route('/', methods=['GET'])
def index():
    print('DOCS ACCESSED')
    return redirect('/api/docs')

@app.route('/DEX_LIST', methods=['GET'])
async def get_dex_list():
    return jsonify(DEX_LIST)

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

@app.route('/health', methods=['GET'])
async def health():
    return jsonify({'status': 'ok'})

@app.route('/order_router', methods=['GET'])
async def order_router():
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    buy_symbol = str(request.args.get('buy_symbol'))
    buy_ID = str(request.args.get('buy_ID'))
    exchanges = request.args.get('exchanges', DEX_LIST)

    print('ORDER ROUTER CALLED')

    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID, exchanges, split=False) # add routing strategy param

    return jsonify(result)

@app.route('/best_match_order_router', methods=['GET'])
async def best_match_order_router():
    sell_symbol = str(request.args.get('sell_symbol'))
    sell_ID = str(request.args.get('sell_ID'))
    sell_amount = float(request.args.get('sell_amount'))
    exchanges = request.args.get('exchanges', DEX_LIST)
    
    buy_symbol = sell_symbol
    buy_ID = sell_ID
    
    print('ORDER ROUTER CALLED')

    result = await route_orders(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID, exchanges, split=True, routing_strategy='best_match')

    return jsonify(result)

@app.route('/refresh_pools', methods=['GET'])
async def refresh_pools_route():
    await refresh_all_pools()
    return jsonify({'status': 'ok'})

def query_process():
    while True:
        time.sleep(1)
        requests.get('http://localhost:5000/refresh_pools')
        time.sleep(29)

def main():

    threads = [
        Thread(target=pool_thread_task)
    ]

    for thread in threads:
        thread.start()

    return app

if __name__ == '__main__':
    loop.run_until_complete(main())
