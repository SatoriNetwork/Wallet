from satoriwallet.lib.structs import TransactionStruct
from satoriwallet.api.blockchain import Electrumx
import time
import random
import json
import socket
from typing import Union
from satorineuron import config
from satorilib.api.disk import Cache  # Disk
from satorilib.api.wallet import EvrmoreWallet
Cache.setConfig(config)
_evrmoreWallet = EvrmoreWallet(
    config.walletPath('wallet.yaml'),
    reserve=0.01,
    isTestnet=False)
w = _evrmoreWallet()


hostPort = 'electrum2-mainnet.evrmorecoin.org:50002'
e = Electrumx(host=hostPort.split(':')[0], port=int(
    hostPort.split(':')[1]), ssl=True, timeout=5)
e.send('server.version', 'SATORI', '1.10')


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


def getAssetHolders(e, asset='SATORI'):
    import time
    addresses = {}
    lastAddresses = None
    i = 0
    while lastAddresses != addresses:
        lastAddresses = addresses
        print('called')
        x = interpret(
            e.send('blockchain.asset.list_addresses_by_asset', asset, False, 1000, i))
        addresses = {**addresses, **x}
        if len(x) < 1000:
            break
        i = i + 1000
        time.sleep(1)  # incase there's a huge number we throttle
    return addresses
