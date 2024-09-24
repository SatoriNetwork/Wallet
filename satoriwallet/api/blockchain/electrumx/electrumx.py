import logging
import socket
import json
import time
from .connector import Connector


class ElectrumX(Connector):
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(type(self).__name__)
        super(type(self), self).__init__(*args, **kwargs)

    def _receive(self):
        buffer = ''
        while True:
            try:
                raw = self.connection.recv(1024*16).decode('utf-8')
                buffer += raw
                if '\n' in raw:
                    # Assuming messages are newline-terminated, split on the first newline.
                    # This is useful in case multiple messages are received or a message is exactly at the boundary.
                    message, _, buffer = buffer.partition('\n')
                    try:
                        r = json.loads(message)
                        self.log.log(5, "_receive {}".format(r))
                        return r  # Return the parsed JSON object
                    except json.decoder.JSONDecodeError as e:
                        # Log the error and the problematic message part
                        self.log.error(
                            "JSONDecodeError: {} in message: {}".format(e, message))
                        # Optionally, handle incomplete message scenarios by breaking or continuing
                        # For now, let's break to avoid an infinite loop
                        break
            except socket.timeout:
                print("Socket timeout occurred during receive.")
                return None  # Timeout, no message received
            except Exception as e:
                print(f"Socket error during receive: {str(e)}")
                return None
            # Optionally, implement a mechanism to prevent an infinite loop if the server sends data that never includes a newline
        return None  # or return an appropriate error/value

    def send(self, method, *args):
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
