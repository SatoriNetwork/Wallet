import socket
import ssl
import logging
import select


class Connector:
    def __init__(
        self,
        host: str,
        port: int,
        ssl: bool = False,
        timeout: int = 10*60,
        network: str = 'mainnet'
    ):
        # self.log.log(15, "Starting...")
        self.host = host
        self.port = port
        self.ssl = port == 50002 or ssl
        self.timeout = timeout
        self.network = network
        self.connection: socket.socket = None
        self.connection_subscriptions: socket.socket = None
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
        self.disconnect()
        self.connect_connection()
        self.connect_subscriptions()
        
    def reconnect(self):
        try:
            # Check if the socket is still connected
            print("reconnection")
            self.connection.send(b'')  # Sending a no-op to check connection
            self.connection_subscriptions.send(b'')
            return True
        except (socket.error, OSError):
            # Attempt to reconnect if the connection is lost
            print("Connection lost, attempting to reconnect...")
            self.connect()  # Reconnect
            return False  # Return False if reconnection fails

    def reconnect(self):
        '''
        doesn't work. doesn't detect connection loss, and self.connect()
        doesn't solve connection loss
        '''
        try:
            # Check if the socket is still connected
            print("reconnection")
            self.connection.send(b'')  # Sending a no-op to check connection
            self.connection_subscriptions.send(b'')
            return True
        except (socket.error, OSError):
            # Attempt to reconnect if the connection is lost
            print("Connection lost, attempting to reconnect...")
            self.connect()  # Reconnect
            return False  # Return False if reconnection fails

    def connect_connection(self):
        # self.log.log(10, "_connect {} {}".format(self.host, self.port))
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.settimeout(self.timeout)
        if self.ssl:
            # # Create a SSL context with a specific protocol
            # # context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # # Optionally, set up more specific SSL options if needed
            # # context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Example to disable TLSv1 and TLSv1.1
            # # Wrap the socket with the SSL context
            # # self.connection = context.wrap_socket(self.connection, server_hostname=self.host)
            # self.connection = ssl.wrap_socket(self.connection)

            # Create an SSL context that does not verify certificates
            # context = ssl.create_default_context()
            # This ignores certificate verification
            context = ssl._create_unverified_context()
            # context.check_hostname = True
            # context.verify_mode = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.CERT_NONE | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3 | ssl.CERT_OPTIONAL | ssl.OP_NO_COMPRESSION | ssl.OP_NO_TICKET | ssl.CERT_REQUIRED
            # context.verify_mode = ssl.CERT_OPTIONAL

            # Wrap the socket with the SSL context
            self.connection = context.wrap_socket(
                self.connection, server_hostname=self.host)
        try:
            self.connection.connect((self.host, self.port))
        except Exception as e:
            logging.error(
                f'error connecting to {self.host}:{str(self.port)} {e}')
            raise e

    def connect_subscriptions(self):
        self.connection_subscriptions = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.connection_subscriptions.settimeout(self.timeout)
        if self.ssl:
            context = ssl._create_unverified_context()
            self.connection_subscriptions = context.wrap_socket(
                self.connection_subscriptions, server_hostname=self.host)
        try:
            self.connection_subscriptions.connect((self.host, self.port))
        except Exception as e:
            logging.error(
                f'error connecting to {self.host}:{str(self.port)} {e}')
            raise e

    def disconnect(self):
        try:
            self.connection.close()
            self.connection_subscriptions.close()
        except Exception as _:
            pass
        try:
            self.connection_subscriptions.close()
        except Exception as _:
            pass
