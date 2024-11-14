import logging
import random
from typing import Union, Dict
from threading import Thread, Event, Lock
import socket
import time
from satoriwallet.api.blockchain.electrumxlite import ElectrumxLite

logging.basicConfig(level=logging.INFO)


class ElectrumxAPI():
    def __init__(
        self,
        address: str,
        scripthash: str,
        chain: str,
        type: str = 'wallet',

    ):
        self.type = type
        self.chain = chain
        self.address = address
        self.scripthash = scripthash
        self.transactions = None
        self.balance = None
        self.stats = None
        self.banner = None
        self.currency = None
        self.transactionHistory = None

    @staticmethod
    def interpret(decoded: dict) -> Union[dict, None]:
        # print(x.decode('utf-8'))
        # decoded = json.loads(x.decode('utf-8'))
        if decoded is None:
            return None
        if isinstance(decoded, str):
            return {'result': decoded}
        if 'result' in decoded.keys():
            return decoded.get('result')
        if 'error' in decoded.keys():
            return decoded.get('error')
        else:
            return decoded

    def getCurrency(self):
        # >>> b.send("blockchain.scripthash.get_balance", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
        # b'{"jsonrpc":"2.0","result":{"confirmed":18193623332178,"unconfirmed":0},"id":1656046285682}\n'
        result = self._sendRequest(
            'blockchain.scripthash.get_balance', False, self.scripthash)
        return (result or {}).get('confirmed', 0) + (result or {}).get('unconfirmed', 0)

    def getBanner(self):
        try:
            return self._sendRequest('server.banner', False)
        except Exception as e:
            logging.error(f"Error getting banner: {str(e)}")
            return "timeout error - unable to get banner"

    def getTransactionHistory(self):
        # b.send("blockchain.scripthash.get_history", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
        # b'{"jsonrpc":"2.0","result":[{"tx_hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","height":2292586}],"id":1656046324946}\n'
        try:
            return self._sendRequest(
                'blockchain.scripthash.get_history', False, self.scripthash)
        except Exception as e:
            logging.error(f"Error getting transaction history: {str(e)}")
            return []

    def getUnspentCurrency(self):
        return self._sendRequest(
            'blockchain.scripthash.listunspent', False, self.scripthash)

    def getUnspentAssets(self):
        # {'jsonrpc': '2.0', 'result': [{'tx_hash': 'bea0e23c0aa8a4f1e1bb8cda0c6f487a3c0c0e7a54c47b6e1883036898bdc101', 'tx_pos': 0, 'height': 868584, 'asset': 'KINKAJOU/GROOMER1', 'value': 100000000}], 'id': 1719672839478}
        if self.chain == 'Evrmore':
            return self._sendRequest(
                'blockchain.scripthash.listunspent',
                False,
                self.scripthash,
                'SATORI')
        else:
            return self._sendRequest(
                'blockchain.scripthash.listassets',
                False,
                self.scripthash)

    def getBalance(self):
        # {'jsonrpc': '2.0', 'result': {'confirmed': 0, 'unconfirmed': 0}, 'id': 1719672672565}
        if self.chain == 'Evrmore':
            balances = self._sendRequest(
                'blockchain.scripthash.get_asset_balance', False, self.scripthash, 'SATORI')
            return balances.get('confirmed', 0) + balances.get('unconfirmed', 0)
        else:
            return self._sendRequest(
                'blockchain.scripthash.get_asset_balance', False, self.scripthash).get('confirmed', {}).get('SATORI', 0)

        # if self._balance is None:
        #     if self.chain == 'Evrmore':
        #         self.balances = self._sendRequest('blockchain.scripthash.get_balance', False, self.scripthash, 'SATORI')
        #         self._balance = self.balances.get(
        #             'confirmed', 0) + self.balances.get('unconfirmed', 0)
        #     else:
        #         self.balances = self._sendRequest('blockchain.scripthash.get_asset_balance', False, self.scripthash)
        #         self._balance = self.balances.get('confirmed', {}).get('SATORI', 0)
        # return self._balance

    def getStats(self):
        return self._sendRequest('blockchain.asset.get_meta', False, 'SATORI')

    # getTransaction Method to get the transaction
    def getTransaction(self, tx_hash: str, throttle: int = 0.34):
        time.sleep(throttle)
        return self._sendRequest('blockchain.transaction.get', False, tx_hash, True)

    # getAssetBalanceForHolder Method
    def getAssetBalanceForHolder(self, scripthash: str, throttle: int = 1):
        time.sleep(throttle)
        return self._sendRequest('blockchain.scripthash.get_asset_balance', True, scripthash).get('confirmed', {}).get('SATORI', 0)

    # getAssetHolders
    def getAssetHolders(self, target_address: Union[str, None] = None) -> Union[Dict[str, int], bool]:
        if not self.handshake():
            return False
        addresses = {}
        last_addresses = None
        i = 0
        while last_addresses != addresses:
            last_addresses = addresses
            response = self._sendRequest(
                'blockchain.asset.list_addresses_by_asset', False, 'SATORI', False, 1000, i)
            if target_address is not None and target_address in response.keys():
                return {target_address: response[target_address]}
            addresses = {**addresses, **response}
            if len(response) < 1000:
                break
            i += 1000
            time.sleep(1)  # Throttle to avoid hitting server limits
        return addresses

    # broadcast method
    def broadcast(self, raw_tx: str):
        if self.handshake():
            self.sentTx = self._sendRequest(
                'blockchain.transaction.broadcast', True, raw_tx)
        return self.sentTx
