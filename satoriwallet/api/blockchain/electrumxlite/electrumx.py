from typing import Union
import logging
import socket
import json
import time
import threading
from satoriwallet.api.blockchain.electrumxlite.connector import ElectrumxConnectorLite


class ElectrumxLite(ElectrumxConnectorLite):
    def __init__(self, *args, persistent: bool = False, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.lastHandshake = 0
        self.handshaked = None
        self.handshake()
        self.persistent = persistent
        if self.persistent:
            self.pingThread = threading.Thread(self.stayConnected, daemon=True)
            self.pingThread.start()

    def stayConnected(self):
        while True:
            time.sleep(60*3)
            if not self.connected():
                self.connect()
                self.handshake()

    def connected(self) -> bool:
        if not super().connected():
            return False
        try:
            response = self.send('server.ping')
            if response is None:
                return False
            return True
        except Exception as e:
            if not self.persistent:
                logging.error(f'checking connected - {e}')
            return False

    def handshake(self):
        try:
            method = 'server.version'
            name = f'Satori Neuron {time.time()}'
            assetApiVersion = '1.10'
            self.handshaked = self.send(method, name, assetApiVersion)
            self.lastHandshake = time.time()
            return True
        except Exception as e:
            logging.error(f'error in handshake initial {e}')

    def _receive(
        self,
        timeout: Union[int, None] = None
    ) -> Union[dict, list, None]:

        def handleMultipleMessages(buffer: str):
            ''' split on the first newline to handle multiple messages '''
            return buffer.partition('\n')

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
                        message, _, buffer = handleMultipleMessages(buffer)
                        try:
                            r = json.loads(message)
                            return r
                        except json.decoder.JSONDecodeError as e:
                            logging.error((
                                f"JSONDecodeError: {e} in message: {message} "
                                "error in _receive"))
                            break
                except socket.timeout:
                    logging.warning("Socket timeout occurred during receive.")
                    return None
                except Exception as e:
                    logging.error(f"Socket error during receive: {str(e)}")
                    return None
        finally:
            self.connection.settimeout(None)
        return None

    def _preparePayload(self, method: str, *args):
        return (
            json.dumps({
                "jsonrpc": "2.0",
                "id": int(time.time()*10000000),
                "method": method,
                "params": args
            }) + '\n'
        ).encode()

    def send(
        self,
        method: str,
        *args,
        sendOnly: bool = False,
        timeout: Union[int, None] = None,
    ) -> Union[dict, list, None]:
        payload = self._preparePayload(method, *args)
        with self.lock:
            self.connection.send(payload)
            if sendOnly:
                return None
            return self._receive(timeout=timeout)
