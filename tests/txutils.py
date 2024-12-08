import hashlib
from typing import Union
import unittest

import base58
from satorilib.wallet import TxUtils


class TestTxUtils(unittest.TestCase):
    # no need to setup, they're all static methods
    # def setUp(self):
    # Create an instance of TxUtils before each test
    # self.tx_utils = TxUtils()

    def test_fee(self):
        result = TxUtils.estimatedFee(
            inputCount=1,
            outputCount=1,
            feeRate=150000)
        self.assertLess(result, 2*100000000)
        result = TxUtils.estimatedFee(
            inputCount=1, outputCount=1, feeRate=150000)
        # Checks the correct calculation of the fee
        self.assertEqual(result, 300000)

    def test_fee_too_high(self):
        result = TxUtils.estimatedFee(
            inputCount=1, outputCount=1, feeRate=150000)
        # Asserts fee isn't unexpectedly high
        self.assertLessEqual(result, 400000)

    def test_asSats(self):
        result = TxUtils.asSats(amount=1)
        self.assertEqual(result, 1*100000000)
        result = TxUtils.asSats(amount=10)
        self.assertEqual(result, 10*100000000)
        result = TxUtils.asSats(amount=21000000000)
        self.assertEqual(result, 21000000000*100000000)
        result = TxUtils.asSats(amount=.1)
        self.assertEqual(result, .1*100000000)
        result = TxUtils.asSats(amount=.00000001)
        self.assertEqual(result, 1)

    def test_asAmount(self):
        self.assertAlmostEqual(TxUtils.asAmount(100000000), 1.0)
        self.assertAlmostEqual(TxUtils.asAmount(50000000), 0.5)
        self.assertAlmostEqual(TxUtils.asAmount(1), 0.00000001)

    def test_floor(self):
        self.assertEqual(TxUtils.floor(123.456789, 2), 123.45)
        self.assertEqual(TxUtils.floor(0.123456789, 5), 0.12345)
        self.assertEqual(TxUtils.floor(0.1, 0), 0)

    def test_isAmountDivisibilityValid(self):
        self.assertTrue(TxUtils.isAmountDivisibilityValid(0.0001, 4))
        self.assertFalse(TxUtils.isAmountDivisibilityValid(0.00001, 4))
        self.assertTrue(TxUtils.isAmountDivisibilityValid(123.00000000, 8))

    def test_roundDownToDivisibility(self):
        self.assertEqual(TxUtils.roundDownToDivisibility(
            0.123456789, 5), 0.12345)
        self.assertEqual(TxUtils.roundDownToDivisibility(123.456, 2), 123.45)
        self.assertEqual(TxUtils.roundDownToDivisibility(0.123456789, 0), 0)

    def test_intToLittleEndianHex(self):
        self.assertEqual(TxUtils.intToLittleEndianHex(
            100000000), '00e1f505')

    def test_padHexStringTo8Bytes(self):
        self.assertEqual(TxUtils.padHexStringTo8Bytes(
            '00e1f505'), '00e1f50500000000')

    def test_addressToH160Bytes(self):
        # Test with a mock address, assuming valid base58check encoded address
        # Actual address should be replaced with valid example
        self.assertEqual(TxUtils.addressToH160Bytes(
            'RXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV').hex(), 'f05325e90d5211def86b856c9569e54808201290')
        self.assertEqual(TxUtils.addressToH160Bytes(
            'EXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV').hex(), '99f2e5e5c46e84b30697ddd61b18664340d07512')

    def test_hash160ToAddress(self):
        # Assuming mainnet, simple test, replace pubKeyHash with actual hash
        self.assertEqual(TxUtils.hash160ToAddress(
            'f05325e90d5211def86b856c9569e54808201290', b'\x3c'), 'RXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV')
        self.assertEqual(TxUtils.hash160ToAddress(
            '99f2e5e5c46e84b30697ddd61b18664340d07512', (33).to_bytes(1, 'big')), 'EXBurnXXXXXXXXXXXXXXXXXXXXXXZ8ZjfN')


@staticmethod
def hash160ToAddress(pubKeyHash: Union[str, bytes], networkByte: bytes = b'\x3c'):
    # Convert string hash to bytes if necessary
    if isinstance(pubKeyHash, str):
        pubKeyHash = bytes.fromhex(pubKeyHash)

    # Step 1: Prepend the network byte(s)
    prefixedPubKeyHash = networkByte + pubKeyHash

    # Steps 2 & 3: Double SHA-256 hashing
    sha256_1 = hashlib.sha256(prefixedPubKeyHash).digest()
    sha256_2 = hashlib.sha256(sha256_1).digest()

    # Step 4: Add the checksum (first 4 bytes of the second hash)
    checksum = sha256_2[:4]
    finalBinaryAddress = prefixedPubKeyHash + checksum

    # Step 5: Base58Check encode the final binary address
    address = base58.b58encode(finalBinaryAddress).decode()

    # Debug: Uncomment the next line to see the generated values
    print(
        f"Debug -> PubKeyHash: {pubKeyHash.hex()}, Network Byte: {networkByte.hex()}, Address: {address}")

    return address


if __name__ == '__main__':
    unittest.main()
