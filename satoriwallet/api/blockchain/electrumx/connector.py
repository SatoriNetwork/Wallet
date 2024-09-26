import socket
import ssl
import logging
import select


class Connector:
    def __init__(self, host, port, ssl=False, timeout=10*60, network='mainnet'):
        # self.log.log(15, "Starting...")
        self.host = host
        self.port = port
        self.ssl = ssl
        self.timeout = timeout
        self.network = network
        self.connection: socket.socket = None
        print(f'{self.host}:{self.port}', self.network)
        self.connect()

    def connected(self) -> bool:
        if self.connection is None:
            return False
        return True
        # # this solution gave false positives:
        # problem:   File "/Satori/Wallet/satoriwallet/api/blockchain/electrumx/connector.py", line 19, in connected
        #           return self.connection is not None and self.connection.connected
        #           AttributeError: 'SSLSocket' object has no attribute 'connected
        # return self.connection is not None and self.connection.connected
        # try:
        #    # Use select to check if the socket is readable
        #    # which would imply it's either still connected or has been closed
        #    ready = select.select([self.connection], [], [], 0.5)
        #    if ready[0]:
        #        # Perform a non-blocking check
        #        # If recv returns an empty string, the socket is closed
        #        data = self.connection.recv(16, socket.MSG_DONTWAIT)
        #        return len(data) != 0
        #    return True  # No data, but socket is not closed
        # except (socket.error, OSError) as e:
        #    # An error in recv likely means the socket is closed
        #    return False
        # except Exception as e:
        #    return False

    def connect(self):
        # self.log.log(10, "_connect {} {}".format(self.host, self.port))
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.settimeout(self.timeout)
        if self.ssl:
            # Create a SSL context with a specific protocol
            # context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # Optionally, set up more specific SSL options if needed
            # context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Example to disable TLSv1 and TLSv1.1
            # Wrap the socket with the SSL context
            # self.connection = context.wrap_socket(self.connection, server_hostname=self.host)
            self.connection = ssl.wrap_socket(self.connection)
        try:
            self.connection.connect((self.host, self.port))
        except Exception as e:
            logging.error(
                f'error connecting to {self.host}:{str(self.port)} {e}')
            raise e

    def disconnect(self):
        self.connection.close()
