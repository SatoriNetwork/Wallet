class TxUtils():
    ''' utility methods for transactions '''

    @ staticmethod
    def estimatedFee(inputCount: int = 0, outputCount: int = 0, feeRate: int = 150000):
        '''
        0.00150000 rvn per item as simple over-estimate
        this fee is on a per input/output basis and it should cover a asset 
        output which is larger than a currency output. therefore it should 
        always be sufficient for our purposes. usually we're sending 1 asset
        vin and 1 asset vout, and 1 currency vin and 1 currency vout.
        '''

        return (inputCount + outputCount) * feeRate

    @staticmethod
    def estimatedFeeRecursive(txHex: str, feeRate: int = 1100):
        '''
        this assumes you've already created a transaction with the and can
        inspect the size of it to estimate the fee, therere it implies a 
        recursive opperation to create the transaction, because the fee must
        be chosen before the transaction is created. so you would build the
        transaction at least twice, but the fee can be much more optimized.
        1.1 standard * 1000 * 192 bytes = 211,200 sats == 0.00211200 rvn
        see example transaction: https://rvn.cryptoscope.io/tx/?txid=
        3a880d09258075635e1565c06dce3f0091a67da987a63140a60f1d8f80a6625a
        we could even base this off of some reasonable upper bound and the 
        minimum relay fee specified by the electurmx server using 
        blockchain.relayfee(). however, since I'm not willing to write the
        recursive process we're not going to use this function yet.
        feeRate = 1100 # 0.00001100 rvn per byte
        '''
        txSizeInBytes = len(txHex) / 2
        return txSizeInBytes * feeRate

    @staticmethod
    def asSats(amount: float) -> int:
        from evrmore.core import COIN
        return int(amount * COIN)

    @staticmethod
    def asAmount(sats: int, divisibility: int = 8) -> float:
        from evrmore.core import COIN
        result = sats / COIN
        if result == 0:
            return 0
        if divisibility == 0:
            return int(result)
        return round(result, divisibility)

    @staticmethod
    def intToLittleEndianHex(number: int) -> str:
        '''
        100000000 -> "00e1f50500000000"
        # Example
        number = 100000000
        little_endian_hex = intToLittleEndianHex(number)
        print(little_endian_hex)
        '''
        # Convert to hexadecimal and remove the '0x' prefix
        hexNumber = hex(number)[2:]
        # Ensure the hex number is of even length
        if len(hexNumber) % 2 != 0:
            hexNumber = '0' + hexNumber
        # Reverse the byte order
        littleEndianHex = ''.join(
            reversed([hexNumber[i:i+2] for i in range(0, len(hexNumber), 2)]))
        return littleEndianHex

    @staticmethod
    def padHexStringTo8Bytes(hexString: str) -> str:
        '''
        # Example usage
        hex_string = "00e1f505"
        padded_hex_string = pad_hex_string_to_8_bytes(hex_string)
        print(padded_hex_string)
        '''
        # Each byte is represented by 2 hexadecimal characters
        targetLength = 16  # 8 bytes * 2 characters per byte
        return hexString.ljust(targetLength, '0')

    @staticmethod
    def addressToH160Bytes(address) -> bytes:
        '''
        address = "RXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV"
        h160 = address_to_h160(address)
        print(h160)
        print(h160.hex()) 'f05325e90d5211def86b856c9569e54808201290'
        '''
        import base58
        decoded = base58.b58decode(address)
        h160 = decoded[1:-4]
        return h160


class AssetTransaction():
    evr = '657672'
    rvn = '72766e'
    t = '74'
    satoriLen = '06'
    satori = '5341544f5249'

    @staticmethod
    def satoriHex(currency: str) -> str:
        if currency.lower() == 'rvn':
            symbol = AssetTransaction.rvn
        elif currency.lower() == 'evr':
            symbol = AssetTransaction.evr
        else:
            raise Exception('invalid currency')
        return (
            symbol +
            AssetTransaction.t +
            AssetTransaction.satoriLen +
            AssetTransaction.satori)
        
    @staticmethod
    def memoHex(memo: str) -> str:
        return memo.encode('utf-8').hex()


class Validate():
    ''' heuristics '''

    @staticmethod
    def address(address: str, currency: str) -> str:
        return (
            (currency.lower() == 'rvn' and address.startswith('R') and len(address) == 34) or
            (currency.lower() == 'evr' and address.startswith('E') and len(address) == 34))
