import logging
import json
import time
from .connector import Connector


class ElectrumX(Connector):
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(type(self).__name__)
        super(type(self), self).__init__(*args, **kwargs)

    # def _receive(self):
    #    raw = self.connection.recv(1024*16)
    #    try:
    #        r = json.loads(raw)
    #        self.log.log(5, "_receive {}".format(r))
    #    except json.decoder.JSONDecodeError:
    #        print('RAW')
    #        print(raw)
    #    return raw

    def _receive(self):
        buffer = ''
        while True:
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
        print('SEND: ', payload)
        self.connection.send(payload)
        return self._receive()
