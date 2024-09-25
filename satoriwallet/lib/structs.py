from typing import Union


class TransactionStruct():

    def __init__(self, raw, vinVoutsTxs):
        self.txid = self.getTxid(raw)
        self.height = self.getHeight(raw)
        self.confirmations = self.getConfirmations(raw)
        self.sent = self.getSent(raw)
        self.received = self.getReceived(raw, vinVoutsTxs)
        self.memo = self.getMemo(raw)

    def getTxid(self, raw):
        return raw.get('txid', 'unknown txid')

    def getHeight(self, raw):
        return raw.get('height', 'unknown height')

    def getConfirmations(self, raw):
        return raw.get('confirmations', 'unknown confirmations')

    def getSent(self, raw):
        sent = {}
        for vout in raw.get('vout', []):
            if 'asset' in vout:
                name = vout.get('asset', {}).get('name', 'unknown asset')
                amount = float(vout.get('asset', {}).get('amount', 0))
            else:
                name = 'Ravencoin'
                amount = float(vout.get('value', 0))
            if name in sent:
                sent[name] = sent[name] + amount
            else:
                sent[name] = amount
        return sent

    def getReceived(self, raw, vinVoutsTxs):
        received = {}
        for vin in raw.get('vin', []):
            position = vin.get('vout', None)
            for tx in vinVoutsTxs:
                for vout in tx.get('vout', []):
                    if position == vout.get('n', None):
                        if 'asset' in vout:
                            name = vout.get('asset', {}).get(
                                'name', 'unknown asset')
                            amount = float(
                                vout.get('asset', {}).get('amount', 0))
                        else:
                            name = 'Ravencoin'
                            amount = float(vout.get('value', 0))
                        if name in received:
                            received[name] = received[name] + amount
                        else:
                            received[name] = amount
        return received

    def getAsset(self, raw):
        return raw.get('txid', 'not implemented')

    def getMemo(self, raw) -> Union[str, None]:
        '''
        vout: {
            'value': 0.0,
            'n': 502,
            'scriptPubKey': {
                'asm': 'OP_RETURN 707265646963746f7273',
                'hex': '6a0a707265646963746f7273',
                'type': 'nulldata'},
            'valueSat': 0}
        '''
        vouts = raw.get('vout', [])
        vouts.reverse()
        for vout in vouts:
            op_return = vout.get('scriptPubKey', {}).get('asm', '')
            if (
                op_return.startswith('OP_RETURN ') and
                vout.get('value', 0) == 0
            ):
                return op_return[10:]
        return None

    def hexMemo(self) -> Union[str, None]:
        return self.memo

    def bytesMemo(self) -> Union[bytes, None]:
        if self.memo == None:
            return None
        return bytes.fromhex(self.memo)

    def strMemo(self) -> Union[str, None]:
        if self.memo == None:
            return None
        return self.bytesMemo().decode('utf-8')

    def ethMemo(self, valid_eth_address: Union[None, callable]) -> Union[str, None]:
        if self.memo == None:
            return None
        address = f'0x{self.memo}'
        # Validate Ethereum address
        if not callable(valid_eth_address):
            return address
        if is_valid_ethereum_address(address):
            return address
        return None
