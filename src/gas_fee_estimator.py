'''
This script estimates the gas fee for a transaction on the Ethereum mainnet.
'''

# third party imports
from web3 import Web3
import dotenv
from requests.auth import HTTPBasicAuth

# use a .env file to store and retrieve your infura key
secrets = dotenv.dotenv_values(".env")
INFURA_KEY = secrets.get("INFURA_KEY")
INFURA_SECRET = secrets.get("INFURA_SECRET", None)
# this is the current minimum gas required for a transaction on the Ethereum mainnet, but may change in the future
MINIMUM_GAS = 21_000

# get the gas price from the Ethereum mainnet using Web3 and Infura
def get_gas_price() -> float:
    # connect to the Ethereum mainnet
    # put your own infura node here
    if INFURA_SECRET:
        w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}", request_kwargs={'auth': HTTPBasicAuth('', INFURA_SECRET)}))
    else:
        w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))
    # get the gas price
    gas_price = w3.eth.gasPrice
    # convert the gas price to gwei
    gas_price_gwei = w3.fromWei(gas_price, 'gwei')
    # return the gas price in gwei
    # print(gas_price_gwei)
    return gas_price_gwei

def get_gas_fee() -> float:
    # get the gas price in gwei
    gas_price_gwei = get_gas_price()
    # calculate the gas fee
    gas_fee = gas_price_gwei * MINIMUM_GAS
    # return the gas fee
    # print(gas_fee)
    return gas_fee

def get_gas_fee_in_eth() -> float:
    # get the gas fee in gwei
    gas_fee_gwei = get_gas_fee()
    # convert the gas fee to eth
    gas_fee_eth = gas_fee_gwei / 1_000_000_000
    # return the gas fee in eth
    # print(gas_fee_eth)
    return float(gas_fee_eth)