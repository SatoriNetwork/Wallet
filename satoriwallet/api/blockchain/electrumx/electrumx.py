from typing import Union
import logging
import socket
import json
import time
import threading
from satorilib.wallet.api.blockchain.electrumx.connector import Connector


class Electrumx(Connector):
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(type(self).__name__)
        super(type(self), self).__init__(*args, **kwargs)
        self.lock = threading.Lock()  # Lock for general connection
        self.walletSubscriptionLock = threading.Lock()  # Lock for subscriptions
        self.vaultSubscriptionLock = threading.Lock()  # Lock for subscriptions
        self.lastHandshake = 0
        self.handshaked = None
        self.handshake()

    def connect(self) -> bool:
        super().connect()
        super().connectSubscriptions()

    def connected(self) -> bool:
        if self.connection is None:
            return False
        try:
            logging.debug('checking connected')
            # Test the connection by sending a lightweight request
            response = self.send('server.ping')
            if response is None:
                logging.debug('checking connected - False')
                return False
            logging.debug('checking connected - True')
            return True
        except Exception as e:
            self.log.error(f"Connection check failed: {e}")
            logging.debug(f'checking connected - {e}')
            return False
        # if self.send('server.ping') == None:
        #    return False
        # return True

    def connectedSubscription(self, conn: socket.socket) -> bool:
        if conn is None:
            conn = self.connectionWalletSubscription
        if self.connectionWalletSubscription is None:
            return False
        try:
            logging.debug('checking connected')
            # Test the connection by sending a lightweight request
            response = self.send('server.ping')
            if response is None:
                logging.debug('checking connected - False')
                return False
            logging.debug('checking connected - True')
            return True
        except Exception as e:
            self.log.error(f"Connection check failed: {e}")
            logging.debug(f'checking connected - {e}')
            return False
        # if self.send('server.ping') == None:
        #    return False
        # return True

    def connectedWalletSubscription(self) -> bool:
        return self.connectedSubscription(self.connectionWalletSubscription)

    def connectedVaultSubscription(self) -> bool:
        return self.connectedSubscription(self.connectionVaultSubscription)

    def handshake(self):
        try:
            name = f'Satori Neuron {time.time()}'
            assetApiVersion = '1.10'
            logging.debug(f'handshake {name} {assetApiVersion}')
            self.handshaked = self.send(
                'server.version',
                name,
                assetApiVersion)
            self.lastHandshake = time.time()
            self.handshakedWalletSubscription = self.sendWalletSubscription(
                'server.version',
                f'Satori Wallet {time.time()}',
                assetApiVersion)
            self.handshakedVaultSubscription = self.sendVaultSubscription(
                'server.version',
                f'Satori Vault {time.time()}',
                assetApiVersion)
            self.lastHandshakeWalletSubscription = time.time()
            self.lastHandshakeVaultSubscription = time.time()
            return True
        except Exception as e:
            logging.error(f'error in handshake initial {e}')

    def _receive(self, timeout: Union[int, None] = None) -> Union[dict, list, None]:
        if timeout is not None:
            self.connection.settimeout(timeout)
        buffer = ''
        try:
            while True:
                try:
                    raw = self.connection.recv(1024 * 16).decode('utf-8')
                    buffer += raw
                    if raw == '':
                        return None
                    if '\n' in raw:
                        # Split on the first newline to handle multiple messages
                        message, _, buffer = buffer.partition('\n')
                        try:
                            r = json.loads(message)
                            self.log.log(5, "_receive {}".format(r))
                            return r  # Return the parsed JSON object
                        except json.decoder.JSONDecodeError as e:
                            # Log the error and the problematic message part
                            self.log.error(
                                "JSONDecodeError: {} in message: {} error in _receive".format(e, message))
                            # Optionally continue or break depending on the scenario
                            break
                except socket.timeout:
                    self.log.warning("Socket timeout occurred during receive.")
                    return None  # Timeout, no message received
                except Exception as e:
                    self.log.error(f"Socket error during receive: {str(e)}")
                    return None
        finally:
            # Reset the timeout to blocking mode
            self.connection.settimeout(None)
        return None

    def _receiveSubscriptions(self, conn: socket.socket, timeout: Union[int, None] = None) -> Union[dict, list, None]:
        if conn is None:
            conn = self.connectionWalletSubscription
        if timeout is not None:
            conn.settimeout(timeout)
        buffer = ''
        try:
            while True:
                try:
                    raw = conn.recv(
                        1024 * 16).decode('utf-8')
                    buffer += raw
                    if '\n' in raw:
                        # Split on the first newline to handle multiple messages
                        message, _, buffer = buffer.partition('\n')
                        try:
                            r = json.loads(message)
                            self.log.log(5, "_receive {}".format(r))
                            return r  # Return the parsed JSON object
                        except json.decoder.JSONDecodeError as e:
                            # Log the error and the problematic message part
                            self.log.error(
                                "JSONDecodeError: {} in message: {} error in _receiveSubscriptions".format(e, message))
                            # Optionally continue or break depending on the scenario
                            break
                except socket.timeout:
                    self.log.warning("Socket timeout occurred during receive.")
                    return None  # Timeout, no message received
                except Exception as e:
                    self.log.error(f"Socket error during receive: {str(e)}")
                    return None
        finally:
            # Reset the timeout to blocking mode
            conn.settimeout(None)
        return None

    def send(self, method: str, *args, **kwargs):
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": int(time.time()*1000),
            "method": method,
            "params": args
        }) + '\n'
        payload = payload.encode()
        self.log.log(5, "send {} {}".format(method, args))
        with self.lock:
            self.connection.send(payload)
            return self._receive(timeout=kwargs.get('timeout'))

    def sendSubscription(self, conn: socket.socket = None, method: str = None, *args, **kwargs):
        if method is None:
            return ''
        if conn is None:
            conn = self.connectionWalletSubscription
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": int(time.time()*1000),
            "method": method,
            "params": args
        }) + '\n'
        payload = payload.encode()
        self.log.log(5, "send {} {}".format(method, args))
        conn.send(payload)
        return f'subscribed to {payload}'

    def sendWalletSubscription(self, method, *args, **kwargs):
        with self.walletSubscriptionLock:
            return self.sendSubscription(self.connectionWalletSubscription, method, *args, **kwargs)

    def sendVaultSubscription(self, method, *args, **kwargs):
        with self.vaultSubscriptionLock:
            return self.sendSubscription(self.connectionVaultSubscription, method, *args, **kwargs)

    def receiveNotifications(self, conn: socket.socket):
        """
        Continuously listens for notifications from the server.
        """
        while True:
            try:
                update = self._receiveSubscriptions(conn)
                logging.debug('update: {}'.format(update))
                if update and 'method' in update:
                    if update['method'] in ['blockchain.scripthash.subscribe', 'blockchain.headers.subscribe', 'blockchain.scripthash.unsubscribe']:
                        yield update
                    else:
                        logging.debug(
                            f"Received unknown method: {update['method']}")
                elif update is None:
                    logging.debug("Received None update, breaking loop")
                    # break  # Handle the case where the connection might have dropped
            except Exception as e:
                logging.error(f"Error in receiveNotifications: {str(e)}")
                break

    def receiveWalletNotifications(self):
        return self.receiveNotifications(self.connectionWalletSubscription)

    def receiveVaultNotifications(self):
        return self.receiveNotifications(self.connectionVaultSubscription)
