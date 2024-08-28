from typing import Union, List, Dict
import socket
import json
import random
import time
from threading import Thread, Event
from satoriwallet.api.blockchain import ElectrumX
from satoriwallet.lib.structs import TransactionStruct
from satorineuron import logging

class ElectrumXAPI:
    def __init__(self, address: str, scripthash: str, servers: list[str], chain: str, timeout: int = 5, retry_attempts: int = 3):
        self.chain = chain
        self.address = address
        self.scripthash = scripthash
        self.servers = servers
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.conn = None
        self.last_handshake = None
        self.transactions = None

        # Cached results ( Private Values )
        self._balance = None
        self._stats = None
        self._banner = None
        self._currency = None
        self._transaction_history = None
        self.failed_servers = set()
        self._unspent_currency = None
        self._unspent_assets = None

        # Public Values
        self.balance = None
        self.stats = None
        self.banner = None
        self.currency = None
        self.transactionHistory = None
        self.failedServers = []
        # if we fail to connect to a server, remember it so we avoid it.

    @staticmethod
    def interpret(decoded: dict):
        # print(x.decode('utf-8'))
        # decoded = json.loads(x.decode('utf-8'))
        if decoded is None:
            return None
        if 'result' in decoded.keys():
            return decoded.get('result')
        if 'error' in decoded.keys():
            return decoded.get('error')
        else:
            return decoded
        
    def connected(self):
        return self.conn is not None and self.conn.connected()
    
    # New Methods with Refactoring
    # Connect method to connect ElectrumX server
    def connect(self):
        if len(self.servers) == 0:
            raise Exception("No servers available")
        if self.conn is not None:
            return self.conn
        tries = 0
        while tries < self.retry_attempts:
            tries += 1
            hostPort = random.choice(self.servers)
            if hostPort in self.failed_servers:
                continue
            try:
                self.conn = ElectrumX(
                    host=hostPort.split(':')[0],
                    port=int(hostPort.split(':')[1]),
                    ssl=True,
                    timeout=self.timeout
                )
                return self.conn
            except socket.timeout:
                self.failed_servers.add(hostPort)
            except Exception as e:
                self.failed_servers.add(hostPort)
                logging.error(f"Connection error to {hostPort}: {str(e)}")
        raise Exception("Unable to connect to any ElectrumX server")

    # Ensure if the connection is established or not
    # Private Method
    def _ensureConnected(self):
        logging.info("Ensure Connection", self.conn, color='red')
        if not self.conn:
            self.connect()
        elif not self.conn.connected():
            self.connect()

    # Handshake method to create the handshake with the ElectrumX server
    def handshake(self) -> bool:
        logging.info("handshake Connection", self.conn, color='red')
        self._ensureConnected()
        if self.last_handshake and time.time() - self.last_handshake < 60 * 60:
            return True

        for _ in range(self.retry_attempts):
            try:
                name = f'Satori Node {self.address}'
                assetApiVersion = '1.10'
                handshake = ElectrumXAPI.interpret(self.conn.send('server.version', name, assetApiVersion))
                if handshake[0].startswith(f'ElectrumX {self.chain}') and handshake[1] == assetApiVersion:
                    self.last_handshake = time.time()
                    return True
            except Exception:
                self.conn = None  # Force reconnect on the next try

        logging.error("Handshake failed after multiple attempts")
        return False

    # _sendRequest function to send the data through socket to ElectrumX server
    # Private Method
    def _sendRequest(self, method: str, checkConnection = True, *params):
        if checkConnection:
            self._ensureConnected()
            # To check whether the connection is till active or not
            if not self.handshake():
                raise Exception("Handshake failed")

        try:
            response = self.conn.send(method, *params)
            return ElectrumXAPI.interpret(response)
        except socket.timeout as e:
            logging.error(f"Timeout during {method}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error during {method}: {str(e)}")
            raise

    # currency Element
    @property
    def currencyEle(self):
        if self._currency is None:
            result = self._sendRequest('blockchain.scripthash.get_balance', False, self.scripthash)
            self._currency = (result or {}).get('confirmed', 0) + (result or {}).get('unconfirmed', 0)
        return self._currency
    
    # banner Element
    @property
    def bannerEle(self):
        if self._banner is None:
            try:
                self._banner = self._sendRequest('server.banner', False)
            except Exception as e:
                logging.error(f"Error getting banner: {str(e)}")
                self._banner = "timeout error - unable to get banner"
        return self._banner

    # transactionHistory Element method to get the data related to transactions
    @property
    def transactionHistoryEle(self):
        if self._transaction_history is None:
            try:
                self._transaction_history = self._sendRequest('blockchain.scripthash.get_history', False, self.scripthash)
            except Exception as e:
                logging.error(f"Error getting transaction history: {str(e)}")
                self._transaction_history = []
        return self._transaction_history
    
    # unSpentCurrency Element method to get the unSpent currency data
    @property
    def unSpentCurrencyEle(self):
        if self._unspent_currency is None:
            self._unspent_currency = self._sendRequest('blockchain.scripthash.listunspent', False, self.scripthash)
        return self._unspent_currency

    # unSpentAssets Element method to get the unSpent assets data
    @property
    def unSpentAssetsEle(self):
        if self._unspent_assets is None:
            if self.chain == 'Evrmore':
                self._unspent_assets = self._sendRequest('blockchain.scripthash.listunspent', False, self.scripthash, 'SATORI')
            else:
                self._unspent_assets = self._sendRequest('blockchain.scripthash.listassets', False, self.scripthash)
        return self._unspent_assets

    # balance Element for both type of wallet
    @property
    def balanceEle(self):
        if self._balance is None:
            if self.chain == 'Evrmore':
                self.balances = self._sendRequest('blockchain.scripthash.get_balance', False, self.scripthash, 'SATORI')
                self._balance = self.balances.get(
                    'confirmed', 0) + self.balances.get('unconfirmed', 0)
            else:
                self.balances = self._sendRequest('blockchain.scripthash.get_asset_balance', False, self.scripthash)
                self._balance = self.balances.get('confirmed', {}).get('SATORI', 0)
        return self._balance
    
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
            response = self._sendRequest('blockchain.asset.list_addresses_by_asset', False, 'SATORI', False, 1000, i)
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
            self.sentTx = self._sendRequest('blockchain.transaction.broadcast', True, raw_tx)
        return self.sentTx
    
    # get method to get the data
    def get(self, allWalletInfo=False):
        """
        Retrieves various wallet information such as currency balance, asset balance, transaction history, etc.
        If allWalletInfo is True, it also retrieves detailed transaction outputs.
        """
        # Ensure the connection is established and handshake is performed
        if not self.handshake():
            return False

        # Using the new properties to fetch data
        self.currency = self.currencyEle
        self.stats = self._sendRequest('blockchain.asset.get_meta', False, 'SATORI')
        self.banner = self.bannerEle
        self.transactionHistory = self.transactionHistoryEle
        self.unspentCurrency = self.unSpentCurrencyEle
        self.balance = self.balanceEle
        self.unspentAssets = self.unSpentAssetsEle

        # Fetching additional wallet info if requested
        if allWalletInfo:
            self.currencyVouts = [
                self.getTransaction(tx.get('tx_hash')) for tx in self.unspentCurrency
            ]
            self.assetVouts = [
                self.getTransaction(tx.get('tx_hash')) for tx in self.unspentAssets
            ]
            
            self.transactions = []
            for tx in self.transactionHistory:
                raw = self.getTransaction(tx.get('tx_hash', ''))
                txs = [self.getTransaction(vin.get('txid', '')) for vin in raw.get('vin', [])]
                self.transactions.append(TransactionStruct(raw=raw, vinVoutsTxs=txs))

    # Old Methods
    # Currently we are not using this, Once we tested the new methods and if they work fine then we will delete all these methods
    def connectOld(self):
        if len(self.servers) == 0:
            return
        tries = 0
        while tries <= len(self.servers):
            tries += 1
            hostPort = random.choice(self.servers)
            if hostPort in self.failedServers:
                continue
            try:
                return ElectrumX(
                    host=hostPort.split(':')[0],
                    port=int(hostPort.split(':')[1]),
                    ssl=True,
                    timeout=5)
            except socket.timeout:
                self.failedServers.append(hostPort)
                continue
            except Exception as _:
                self.failedServers.append(hostPort)
                continue
        hostPort = random.choice(self.servers)
        return ElectrumX(
            host=hostPort.split(':')[0],
            port=int(hostPort.split(':')[1]),
            ssl=True,
            timeout=5)

    def handshakeOld(self) -> bool:
        logging.info("Handshake initial", self.connected() and self.lastHandshake != None and time.time() - self.lastHandshake < 60*60, color='red')
        if self.connected() and self.lastHandshake != None and time.time() - self.lastHandshake < 60*60:
            # not sure if this will always work well. what if our handshake is
            # no longer valid? or we get disconnected somehow but don't know it?
            # if we run into problems we might have to handskake every time.
            # we only need to check into the server on occasion to send a
            # transaction or get a bunch of data at once during startup. we
            # could say, if the last time we attempted to handskake was more
            # than an hour ago, just reconnect, else return True if we think
            # we're still connected.
            return True
        i = 0
        self.conn = None
        while self.conn == None and i < 5:
            i += 1
            self.conn = self.connect()
            name = f'Satori Node {self.address}'
            assetApiVersion = '1.10'
            try:
                handshake = ElectrumXAPI.interpret(self.conn.send(
                    'server.version',
                    name,
                    assetApiVersion))
                break
            except socket.timeout:
                self.conn = None
                continue
        if self.conn == None:
            return False
            # raise Exception('unable to connect to electrumx servers')
        if (
            handshake[0].startswith(f'ElectrumX {self.chain}')
            and handshake[1] == assetApiVersion
        ):
            self.lastHandshake = time.time()
            return True
        return False

    def getOld(self, allWalletInfo=False):
        '''
        this needs to be moved out into an interface with the blockchain,
        but we don't have that module yet. so it's all basically hardcoded for now.

        get_asset_balance
        {'confirmed': {'SATORI!': 100000000, 'SATORI': 100000000000000}, 'unconfirmed': {}}
        get_meta
        {'sats_in_circulation': 100000000000000, 'divisions': 0, 'reissuable': True, 'has_ipfs': False, 'source': {'tx_hash': 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3', 'tx_pos': 3, 'height': 2292586}}
        '''

        # def invertDivisibility(divisibility:int):
        #    return (16 + 1) % (divisibility + 8 + 1);
        #
        # def removeStringedZeros():
        #
        #    return self.balance[0:len(self.balance) - invertDivisibility(int(self.stats.get('divisions', 8)))]
        #
        # def removeZeros():
        #    return self.balance /
        #
        # def splitBalanceOnDivisibility():
        #    return self.balance / int('1' + ('0'*invertDivisibility(int(self.stats.get('divisions', 8)))) )
        logging.info("Getting connection value", self.conn, color='red')
        if not self.handshake():
            return False
        currency = ElectrumXAPI.interpret(self.conn.send(
            'blockchain.scripthash.get_balance',
            self.scripthash))
        self.currency = (
            (currency or {}).get('confirmed', 0) +
            (currency or {}).get('unconfirmed', 0))
        # >>> b.send("blockchain.scripthash.get_balance", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
        # b'{"jsonrpc":"2.0","result":{"confirmed":18193623332178,"unconfirmed":0},"id":1656046285682}\n'
        self.stats = ElectrumXAPI.interpret(self.conn.send(
            'blockchain.asset.get_meta',
            'SATORI'))
        try:
            self.banner = ElectrumXAPI.interpret(
                self.conn.send('server.banner'))
        except Exception as e:
            print('error getting banner', e)
            self.banner = "timeout error - unable to get banner"
        try:
            # b.send("blockchain.scripthash.get_history", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
            # b'{"jsonrpc":"2.0","result":[{"tx_hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","height":2292586}],"id":1656046324946}\n'
            self.transactionHistory = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.scripthash.get_history',
                self.scripthash))
        except Exception as e:
            print('error getting transaction history', e)
            self.transactionHistory = []
        self.unspentCurrency = ElectrumXAPI.interpret(self.conn.send(
            'blockchain.scripthash.listunspent',
            self.scripthash))
        if self.chain == 'Evrmore':
            # {'jsonrpc': '2.0', 'result': {'confirmed': 0, 'unconfirmed': 0}, 'id': 1719672672565}
            self.balances = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.scripthash.get_balance',
                self.scripthash,
                'SATORI'))
            self.balance = self.balances.get(
                'confirmed', 0) + self.balances.get('unconfirmed', 0)
            # {'jsonrpc': '2.0', 'result': [{'tx_hash': 'bea0e23c0aa8a4f1e1bb8cda0c6f487a3c0c0e7a54c47b6e1883036898bdc101', 'tx_pos': 0, 'height': 868584, 'asset': 'KINKAJOU/GROOMER1', 'value': 100000000}], 'id': 1719672839478}
            self.unspentAssets = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.scripthash.listunspent',
                self.scripthash,
                'SATORI'))
        else:
            self.balance = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.scripthash.get_asset_balance',
                self.scripthash)
            ).get('confirmed', {}).get('SATORI', 0)
            self.unspentAssets = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.scripthash.listassets',
                self.scripthash))

        # we don't actually need this, we can regenerate the asset script.
        # self.assetTransactions = []
        # for unspentAssetHash in [
        #    ua.get('tx_hash') for ua in self.unspentAssets
        #    if ua.get('tx_hash') is not None
        # ]:
        #    self.assetTransactions.append(ElectrumXAPI.interpret(self.conn.send(
        #        'blockchain.transaction.get',
        #        unspentAssetHash, True)))
        if allWalletInfo:
            # I don't actually have to get the vouts because listassets
            # gives me everything I need to make a transaction:
            # {"tx_hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3",
            # "tx_pos":3,"height":2292586,"name":"SATORI",
            # "value":100000000000000}
            # at first I thought that tx_hash was the creation of the asset,
            # but no, it's what I want it to be.
            self.currencyVouts = []
            for tx in self.unspentCurrency:
                self.currencyVouts.append(ElectrumXAPI.interpret(self.conn.send(
                    'blockchain.transaction.get',
                    tx.get('tx_hash'), True)))
            self.assetVouts = []
            for tx in self.unspentAssets:
                self.assetVouts.append(ElectrumXAPI.interpret(self.conn.send(
                    'blockchain.transaction.get',
                    tx.get('tx_hash'), True)))
        if allWalletInfo:
            self.transactions = []
            for tx in self.transactionHistory:
                raw = ElectrumXAPI.interpret(self.conn.send(
                    'blockchain.transaction.get',
                    tx.get('tx_hash', ''), True))
                txs = []
                for vin in raw.get('vin', []):
                    txs.append(ElectrumXAPI.interpret(self.conn.send(
                        'blockchain.transaction.get',
                        vin.get('txid', ''), True)))
                self.transactions.append(
                    TransactionStruct(raw=raw, vinVoutsTxs=txs))
                # >>> b.send("blockchain.transaction.get", 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3')
                # b'{"jsonrpc":"2.0","result":"0200000001aece4f378e364682d77ea345581f4880edd0709c2bf524320b223e7c66aaf25b000000006a473044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a012103571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8affffffff0400743ba40b0000001976a914f62e63b933953a680f3c3a63324948293ba47d1688ac52b574088c1000001976a9143d5143a9336eaf44990a0b4249fcb823d70de52c88ac00000000000000002876a9143d5143a9336eaf44990a0b4249fcb823d70de52c88acc00c72766e6f075341544f5249217500000000000000003276a9143d5143a9336eaf44990a0b4249fcb823d70de52c88acc01672766e71065341544f524900407a10f35a00000001007500000000","id":1656046440320}\n'
                # print(bytes.fromhex('68656c6c6f').decode('utf-8'))

    def getTransactionOld(self, txHash: str, throttle: int = .34):
        ''' using a throttle here because this is often used to get lists in a dataframe apply method'''
        import time
        time.sleep(throttle)
        return ElectrumXAPI.interpret(self.conn.send(
            'blockchain.transaction.get',
            txHash, True))

    def getAssetForHolderOld(self, scripthash: str, throttle: int = 1):
        ''' using a throttle here because this is often used to get lists in a dataframe apply method'''
        import time
        time.sleep(throttle)
        return ElectrumXAPI.interpret(self.conn.send(
            'blockchain.scripthash.get_asset_balance',
            scripthash)).get('confirmed', {}).get('SATORI', 0)

    def getAssetHoldersOld(self, targetAddress: Union[str, None] = None) -> Union[dict[str, int], bool]:
        '''
        gives back a full list of wallets and their amounts of a particular asset. 
        loops until it gets the full list.
        '''
        import time
        if not self.handshake():
            return False
        addresses = {}
        lastAddresses = None
        i = 0
        while lastAddresses != addresses:
            lastAddresses = addresses
            x = ElectrumXAPI.interpret(self.conn.send(
                'blockchain.asset.list_addresses_by_asset',
                'SATORI', False, 1000, i))
            if targetAddress is not None and targetAddress in x.keys():
                return {targetAddress: x[targetAddress]}
            addresses = {**addresses, **x}
            if len(x) < 1000:
                break
            i = i + 1000
            time.sleep(1)  # incase there's a huge number we throttle
        return addresses

    def broadcastOld(self, rawTx: str):
        if self.handshake():
            sent = self.conn.send('blockchain.transaction.broadcast', rawTx)
            self.sentTx = ElectrumXAPI.interpret(sent)
        return self.sentTx

# transaction history
# private key
# qr address
# address
# send
# electrum banner
# about Satori Token - asset on rvn, will be fully convertable to it's own blockchain when Satori is fully decentralized

# >>> b.send("blockchain.scripthash.get_balance", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
# b'{"jsonrpc":"2.0","result":{"confirmed":18193623332178,"unconfirmed":0},"id":1656046285682}\n'

# b.send("blockchain.scripthash.get_history", script_hash('REsQeZT8KD8mFfcD4ZQQWis4Ju9eYjgxtT'))
# b'{"jsonrpc":"2.0","result":[{"tx_hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","height":2292586}],"id":1656046324946}\n'

# >>> b.send("blockchain.transaction.get", 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3')
# b'{"jsonrpc":"2.0","result":"0200000001aece4f378e364682d77ea345581f4880edd0709c2bf524320b223e7c66aaf25b000000006a473044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a012103571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8affffffff0400743ba40b0000001976a914f62e63b933953a680f3c3a63324948293ba47d1688ac52b574088c1000001976a9143d5143a9336eaf44990a0b4249fcb823d70de52c88ac00000000000000002876a9143d5143a9336eaf44990a0b4249fcb823d70de52c88acc00c72766e6f075341544f5249217500000000000000003276a9143d5143a9336eaf44990a0b4249fcb823d70de52c88acc01672766e71065341544f524900407a10f35a00000001007500000000","id":1656046440320}\n'
# print(bytes.fromhex('68656c6c6f').decode('utf-8'))

# >>> b.send("blockchain.transaction.get", 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3', True)
# RAW
# b'{"jsonrpc":"2.0","result":{"txid":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","version":2,"size":333,"vsize":333,"locktime":0,"vin":[{"txid":"5bf2aa667c3e220b3224f52b9c70d0ed80481f5845a37ed78246368e374fceae","vout":0,"scriptSig":{"asm":"3044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a[ALL] 03571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8a","hex":"473044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a012103571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8a"},"sequence":4294967295}],"vout":[{"value":500.0,"n":0,"scriptPubKey":{"asm":"OP_DUP OP_HASH160 f62e63b933953a680f3c3a63324948293ba47d16 OP_EQUALVERIFY OP_CHECKSIG","hex":"76a914f62e63b933953a680f3c3a63324948293ba47d1688ac","reqSigs":1,"type":"pubkeyhash",'
# b'{"jsonrpc":"2.0","result":{"txid":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","hash":"a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3","version":2,"size":333,"vsize":333,"locktime":0,"vin":[{"txid":"5bf2aa667c3e220b3224f52b9c70d0ed80481f5845a37ed78246368e374fceae","vout":0,"scriptSig":{"asm":"3044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a[ALL] 03571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8a","hex":"473044022079b86eae8bf1974be0134387f6db11a49f273660ec2ea0ce98bb5cf31dfb70d702200b1d46a748f2dea4753175f9f695a16dfdbdbdb50400076cd28165795a80b30a012103571524d47ad9240a9674c2085959c60ea62c5d5567b62e0bfd4d40727bba7a8a"},"sequence":4294967295}],"vout":[{"value":500.0,"n":0,"scriptPubKey":{"asm":"OP_DUP OP_HASH160 f62e63b933953a680f3c3a63324948293ba47d16 OP_EQUALVERIFY OP_CHECKSIG","hex":"76a914f62e63b933953a680f3c3a63324948293ba47d1688ac","reqSigs":1,"type":"pubkeyhash",'
# >>>
