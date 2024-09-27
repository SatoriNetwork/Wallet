from typing import Union, Dict
from threading import Thread, Event
import socket
import time
from satoriwallet.api.blockchain import Electrumx


class ElectrumxAPI():
    def __init__(
        self,
        address: str,
        scripthash: str,
        servers: list[str],
        chain: str,
        connection: Electrumx = None,
        type: str = 'wallet',
        timeout: int = 5,
        retry_attempts: int = 3,
        onScripthashNotification=None,
        onBlockNotification=None,
    ):
        self.chain = chain
        self.address = address
        self.scripthash = scripthash
        self.servers = servers
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.conn = connection
        self.last_handshake = time.time()
        self.transactions = None
        self.subscriptions = {}
        self.stop_all_subscriptions = Event()
        self.balance = None
        self.stats = None
        self.banner = None
        self.currency = None
        self.transactionHistory = None
        self.onScripthashNotification = onScripthashNotification
        self.onBlockNotification = onBlockNotification
        self.lastBlockTime = 0
        self.type = type

    def connected(self):
        if (
            self.subscriptions.get('block') is not None and
            self.lastBlockTime + 5*60 < time.time()
        ):
            return False
        return self.conn is not None and self.conn.connected()

    def connect(self):
        if len(self.servers) == 0:
            raise Exception("No servers available")
        if self.connected():
            return self.conn
        tries = 0
        while tries <= self.retry_attempts:
            tries += 1
            try:
                self.conn.connect()
                if self.connected():
                    self.handshake()
                    self.makeSubscriptions()
            except Exception as _:
                time.sleep(1)

    # Ensure if the connection is established or not
    def _ensureConnected(self):
        if not self.connected():
            self.connect()

    def handshake(self) -> bool:
        self._ensureConnected()
        if self.connected() and self.last_handshake != None and time.time() - self.last_handshake < 60*60:
            return True
        if not self.connected():
            raise Exception('unable to connect to electrumx servers')
        for _ in range(self.retry_attempts):
            try:
                name = f'Satori Node {self.address}'
                assetApiVersion = '1.10'
                handshake = ElectrumxAPI.interpret(self.conn.send(
                    'server.version',
                    name,
                    assetApiVersion))
                if (
                    handshake[0].startswith(f'Electrumx {self.chain}')
                    and handshake[1] == assetApiVersion
                ):
                    self.last_handshake = time.time()
                    return True
            except Exception as e:
                print(f'error in handshake {e}')
                continue
        print("Handshake failed after multiple attempts")
        self.conn.disconnect()
        return False

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

    # _sendRequest function to send the data through socket to Electrumx server
    # Private Method

    def _sendRequest(self, method: str, checkConnection=True, *params):
        if checkConnection:
            self._ensureConnected()
            # To check whether the connection is till active or not
            if not self.handshake():
                raise Exception("Handshake failed")
        try:
            response = self.conn.send(method, *params)
            print(f"!!!!!!!!!!!!!!Response Got!!!!!!!!!!! {method}")
            return ElectrumxAPI.interpret(response)
        except socket.timeout as e:
            print(f"Timeout during {method}: {str(e)}")
            raise
        except Exception as e:
            print(f"Error during {method}: {str(e)}")
            raise

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
            print(f"Error getting banner: {str(e)}")
            return "timeout error - unable to get banner"

    def getTransactionHistory(self):
        # b.send("blockchain.scripthash.get_history", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
        # b'{"jsonrpc":"2.0","result":[{"tx_hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","height":2292586}],"id":1656046324946}\n'
        try:
            return self._sendRequest(
                'blockchain.scripthash.get_history', False, self.scripthash)
        except Exception as e:
            print(f"Error getting transaction history: {str(e)}")
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
                'blockchain.scripthash.get_balance', False, self.scripthash, 'SATORI')
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
            addresses.update(response)
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

    # make all subscriptions - handles cleaning up stale subscriptions
    def makeSubscriptions(self):
        if self.subscriptions.get('scripthash') != None or self.subscriptions.get('block') != None:
            self.stop_all_subscriptions.set()
            self.stopScripthashSubscription()
            self.stopHeaderSubscription()
        print("Starting the Subscriptions")
        self.stop_all_subscriptions.clear()
        self.subscribeScriptHash()
        if self.type == 'vault':
            self.subscribeBlockHeaders()

    # New method for subscribing to a scripthash and listening for updates
    def subscribeScriptHash(self):
        """
        Subscribe to the scripthash and start listening for updates.
        """
        if not self.connected():
            raise Exception("Not connected to Electrumx server.")

        # Ensure the connection is established and handshake is performed
        print("subscribeScriptHash started")
        if not self.handshake():
            raise Exception("Not connected to Electrumx server.")

        # Subscribe to the scripthash
        initial_status = self._sendRequest(
            'blockchain.scripthash.subscribe', False, self.scripthash)
        print(
            f"Initial status for scripthash {self.scripthash}: {initial_status}")

        # Start a thread to listen for updates
        self.subscriptions['scripthash'] = Thread(
            target=self._processNotifications)
        self.subscriptions['scripthash'].start()

    # New method for subscribing to a scripthash and listening for updates
    def subscribeBlockHeaders(self):
        """
        Subscribe to the scripthash and start listening for updates.
        """
        if not self.connected():
            raise Exception("Not connected to Electrumx server.")

        # Ensure the connection is established and handshake is performed
        print("subscribeBlockHeaders started")
        if not self.handshake():
            raise Exception("Not connected to Electrumx server.")

        # Subscribe to the headers for new block
        initial_status_header = self._sendRequest(
            'blockchain.headers.subscribe', False)
        print(f"Initial status for header: {initial_status_header}")

        # Start a thread to listen for updates
        self.subscriptions['block'] = Thread(
            target=self._processNotifications)
        self.subscriptions['block'].start()

    # _processNotifications method to listening for updates
    def _processNotifications(self):
        """
        Processes incoming notifications for the subscribed scripthash and headers.
        """
        print("_processNotifications started")

        try:
            for notification in self.conn.receive_notifications():
                print(f"Received notification {notification}")
                if self.stop_all_subscriptions.is_set():
                    print("Stop event set, breaking loop")
                    break

                if 'method' in notification:
                    if notification['method'] == 'blockchain.scripthash.subscribe':
                        if 'params' in notification and len(notification['params']) == 2:
                            scripthash, status = notification['params']
                            if self.scripthash == scripthash:
                                print(
                                    f"Received update for scripthash {scripthash}: {status}")
                                if callable(self.onScripthashNotification):
                                    self.onScripthashNotification(notification)
                    elif notification['method'] == 'blockchain.headers.subscribe':
                        if 'params' in notification and len(notification['params']) > 0:
                            header = notification['params'][0]
                            print(
                                f"Received new block header: height {header.get('height')}, hash {header.get('hex')[:64]}")
                            self.lastBlockTime = time.time()
                            if callable(self.onBlockNotification):
                                self.onBlockNotification(notification)
                    else:
                        print(
                            f"Received unknown method: {notification['method']}")
        except Exception as e:
            print(f"Error in _processNotifications: {str(e)}")

        print("_processNotifications ended")

    # Method to stop subscription
    # unsubscribe from the Electrumx server
    # Stop the event and thread
    def stopScripthashSubscription(self):
        """
        Stops the subscription thread.
        """
        print(f"Stop scripthash subscription started {self.subscriptions['scripthash']}")

        if self.subscriptions['scripthash'] and self.subscriptions['scripthash'].is_alive():
            # Unsubscribe from the scripthash
            try:
                self._sendRequest(
                    'blockchain.scripthash.unsubscribe', True, self.scripthash)
                print(
                    f"Unsubscribed from scripthash {self.scripthash}")
            except Exception as e:
                print(
                    f"Error while unsubscribing from scripthash {self.scripthash}: {str(e)}")

            self.subscriptions['scripthash'].join()
            print(
                f"Stopped subscription thread for scripthash {self.scripthash}")

    # Method to stop subscription
    # unsubscribe from the Electrumx server
    # Stop the event and thread
    def stopHeaderSubscription(self):
        """
        Stops the subscription thread.
        """
        print(f"Stop header subscription started {self.subscriptions['block']}")

        if self.subscriptions['block'] and self.subscriptions['block'].is_alive():
            # Unsubscribe from the header subscription
            try:
                self._sendRequest('blockchain.headers.unsubscribe', True)
                print("Unsubscribed from headers")
            except Exception as e:
                print(f"Error while unsubscribing from headers: {str(e)}")

            self.subscriptions['block'].join()
            print(
                f"Stopped header subscription thread")
