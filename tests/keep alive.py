import os
from satorilib.disk import Disk
from satorilib.wallet import RavencoinWallet, EvrmoreWallet
from satorineuron import config
Disk.setConfig(config)
w = EvrmoreWallet(walletPath=config.walletPath('wallet.yaml'))
w.electrumx
w()
w.setupSubscriptions()
w.subscribe()
w.keepAlive()
w.connected()
w.disconnect()
w.disconnectSubscriptions()
w.connected()
w.connectedSubscriptions()
