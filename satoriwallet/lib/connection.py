# a satori node uses the wallet public key to connect to the server via signing a message.
# the message is the date in UTC now that way the server doesn't have to give the client
# a message to sign. so the client just sends up the public key and the sig. done.
import datetime as dt


def authPayload(wallet, challenge: str = None):
    ''' see wallet_auth in server '''
    challenge = challenge or getFullDateMessage()
    print('AUTH PAYLOAD TIMEMSG: --- ', challenge)
    return {
        'message': challenge,
        'pubkey': wallet.publicKey,
        'address': wallet.address,
        'signature': wallet.sign(challenge).decode()}


def getFullDateMessage():
    ''' returns a string of today's date in UTC like this: "2022-08-01 17:28:44.748691" '''
    x = dt.datetime.utcnow()
    print('AUTH PAYLOAD TIME: --- ', x)
    return str(x)
