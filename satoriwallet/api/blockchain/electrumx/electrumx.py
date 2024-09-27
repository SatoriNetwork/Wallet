from typing import Union
import logging
import socket
import json
import time
from .connector import Connector


class Electrumx(Connector):
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(type(self).__name__)
        super(type(self), self).__init__(*args, **kwargs)
        self.last_handshake = 0
        self.handshaked = None
        self.handshake()

    def connected(self) -> bool:
        if self.connection is None:
            return False
        try:
            # self.connection.settimeout(10)
            return True
        except Exception as e:
            self.log.error(f"error setting timeout {e}")
            return False
        #if self.send('server.ping') == None:
        #    return False
        #return True

    def handshake(self):
        try:
            name = f'Satori Node {time.time()}'
            assetApiVersion = '1.10'
            print(f'handshake {name} {assetApiVersion}')
            self.handshaked = self.send(
                'server.version',
                name,
                assetApiVersion)
            self.last_handshake = time.time()
            return True
        except Exception as e:
            print(f'error in handshake initial {e}')

    def _receive(self, timeout: Union[int, None] = None) -> Union[dict, list, None]:
        if timeout is not None:
            self.connection.settimeout(timeout)
        buffer = ''
        try:
            while True:
                try:
                    raw = self.connection.recv(1024 * 16).decode('utf-8')
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
                                "JSONDecodeError: {} in message: {}".format(e, message))
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

    def send(self, method, *args, **kwargs):
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": int(time.time()*1000),
                "method": method,
                "params": args
            }
        ) + '\n'
        payload = payload.encode()
        self.log.log(5, "send {} {}".format(method, args))
        self.connection.send(payload)
        return self._receive()

    def receive_notifications(self):
        """
        Continuously listens for notifications from the server.
        """
        while True:
            try:
                update = self._receive()
                if update and 'method' in update:
                    if update['method'] in ['blockchain.scripthash.subscribe', 'blockchain.headers.subscribe']:
                        yield update
                    else:
                        print(f"Received unknown method: {update['method']}")
                elif update is None:
                    print("Received None update, breaking loop")
                    break  # Handle the case where the connection might have dropped
            except Exception as e:
                print(f"Error in receive_notifications: {str(e)}")
                break
