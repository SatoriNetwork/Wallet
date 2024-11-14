import ssl
import logging
import asyncio
import websockets
from websockets import WebSocketClientProtocol

logging.basicConfig(level=logging.INFO)

# import websocket
# import ssl
#
# Correct IP address and port (ensure they are correct and supported by the server)
# url = '128.199.1.149'
# port = '50002'
# ws_url = f'wss://{url}:{port}'  # Use wss if using SSL
#
# try:
#    # Create WebSocket connection
#    ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})  # Avoid certificate verification for testing
#    ws.connect(ws_url)
#    # Send a test ping to check connection
#    ws.send("{\"method\": \"server.ping\", \"id\": 1}")
#    # Receive a response
#    response = ws.recv()
#    print("Response:", response)
# except Exception as e:
#    print("Connection failed:", e)


class ElectrumxWebsocketLite:
    def __init__(
        self,
        host: str,
        port: int,
        ssl: bool = False,
        timeout: int = 10 * 60,
    ):
        self.host = host
        self.port = port
        self.ssl = port == 50002 or ssl
        self.timeout = timeout
        self.ws: WebSocketClientProtocol = None
        self.loop = asyncio.get_event_loop()
        self.connect()

    def connected(self) -> bool:
        return self.ws is not None and self.ws.open

    def reconnect(self):
        self.loop.run_until_complete(self.disconnect())
        self.connect()

    def connect(self):
        url = f"{'wss' if self.ssl else 'ws'}://{self.host}:{self.port}"
        self.loop.run_until_complete(self._connect(url))

    async def _connect(self, url: str):
        try:
            ssl_context = None
            if self.ssl:
                ssl_context = ssl._create_unverified_context()
            self.ws = await websockets.connect(url, ssl=ssl_context)
            logging.info(f"Connected to {url}")
        except Exception as e:
            logging.error(f"Error connecting to {url}: {e}")
            raise e

    async def disconnect(self):
        if self.ws is not None:
            try:
                await self.ws.close()
                logging.info("WebSocket disconnected.")
            except Exception as e:
                logging.error(f"Error disconnecting WebSocket: {e}")

    def send(self, message: str):
        self.loop.run_until_complete(self._send(message))

    async def _send(self, message: str):
        if not self.connected():
            logging.error("WebSocket is not connected. Cannot send message.")
            return
        try:
            await self.ws.send(message)
            logging.info(f"Message sent: {message}")
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def receive(self):
        return self.loop.run_until_complete(self._receive())

    async def _receive(self):
        if not self.connected():
            logging.error(
                "WebSocket is not connected. Cannot receive message.")
            return None
        try:
            response = await self.ws.recv()
            logging.info(f"Message received: {response}")
            return response
        except Exception as e:
            logging.error(f"Error receiving message: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    connector = ElectrumxWebsocketLite("electrum.example.com", 50002, ssl=True)
    connector.send("{\"method\": \"server.ping\", \"id\": 1}")
    response = connector.receive()
    print(response)
    connector.reconnect()
