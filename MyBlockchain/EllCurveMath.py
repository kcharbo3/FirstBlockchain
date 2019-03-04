from fastecdsa import keys, curve
import hashlib
import binascii

'''
Does all of the encryption math.
Fastecdsa is only imported to generate a private key, all other math such as calculating public key is done here.
Uses Bitcoin math, so a private key here leads to the same address and public key it would on the bitcoin network.
'''
class EllCurveMath:

    def __init__(self):
        self.p = (2**256) - (2**32) - (2**9) - (2**8) - (2**7) - (2**6) - (2**4) - 1
        self.n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        self.G = [0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798, 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8]
        self.base58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"



    #returns type long
    def createPrivKey(self):
        priv_key = keys.gen_private_key(curve.P256)
        return priv_key



    def getPubKey(self, pK):
        pubK = self.multiplyPoint(self.G, pK)
        return pubK


    def getPubKeyHash(self, pubK):
        pk1 = hex(pubK[0])[2:]
        pk2 = hex(pubK[1])[2:]
        len1, len2 = len(pk1), len(pk2)
        while len1 < 64:
            pk1 = "0" + pk1
            len1 = len(pk1)
        while len2 < 64:
            pk2 = "0" + pk2
            len2 = len(pk2)

        pubK = "04" + pk1 + pk2
        ripeMD = hashlib.new('ripemd160')
        ripeMD.update(binascii.unhexlify(hashlib.sha256((binascii.unhexlify(pubK))).hexdigest()))
        hashedK = ripeMD.hexdigest()
        return hashedK

    def getAddress(self, pubK):
        prefixHashed = "00" + self.getPubKeyHash(pubK)
        checksum = hashlib.sha256(binascii.unhexlify(hashlib.sha256(binascii.unhexlify(prefixHashed)).hexdigest())).hexdigest()
        checksum = checksum[:8]
        checkedK = prefixHashed + checksum
        return self.toBase58(checkedK)

    def getAddressPubKH(self, pubKH):
        prefixHashed = "00" + pubKH
        checksum = hashlib.sha256(binascii.unhexlify(hashlib.sha256(binascii.unhexlify(prefixHashed)).hexdigest())).hexdigest()
        checksum = checksum[:8]
        checkedK = prefixHashed + checksum
        return self.toBase58(checkedK)


    def addPoint(self, p1, p2):
        if p1[0] == p2[0] and p1[1] == p2[1]:
            sDen = (2 * p1[1]) % self.p
            sNum = (3 * ((p1[0]**2) % self.p)) % self.p

            sDen = pow(sDen, self.p - 2, self.p)

            s = (sNum * sDen) % self.p

            x = (((s**2) % self.p) - ((2 * p1[0]) % self.p)) % self.p
            y = (-((p1[1] + ((s * ((x - p1[0]) % self.p)) % self.p)) % self.p)) % self.p
            return [x, y]


        sDen = (p2[0] - p1[0]) % self.p
        sNum = (p2[1] - p1[1]) % self.p

        sDen = pow(sDen, self.p - 2, self.p)
        s = (sNum * sDen) % self.p
        x = (((((s**2) % self.p) - p1[0]) % self.p) - p2[0]) % self.p
        y = (((s*((p1[0] - x) % self.p)) % self.p) - p1[1]) % self.p
        return [x, y]


    #pass scalar as type long
    def multiplyPoint(self, point, scalar):
        scalar = bin(scalar)[2:]
        P = point
        Q = None
        for i in reversed(scalar):
            if i == '1':
                if Q is None:
                    Q = P
                else:
                    Q = self.addPoint(Q, P)
            P = self.addPoint(P, P)
        return Q


    #num should be hex string
    def toBase58(self, num):
        b58 = ''
        hexnum = num
        num = int(num, 16)
        if num <= 58:
            return self.base58[num]

        count = 0
        while count < 2:
            char = int(num % 58)
            b58 = self.base58[char] + b58
            num = num // 58
            if num <= 58:
                count = count + 1

        for i in range(0, len(hexnum), 2):
            if hexnum[i:i + 2] == "00":
                b58 = '1' + b58
            else:
                break
        return b58

    #privK in type long, txHash in string hex
    def signature(self, privK, txHash):
        tempPrivK = self.createPrivKey()
        tempPubK = self.getPubKey(tempPrivK)
        R = tempPubK[0]
        S = (pow(tempPrivK, self.n - 2, self.n) * ((int(txHash, 16) + ((privK * R) % self.n)) % self.n)) % self.n
        sig = [R, S]
        return sig

    def verifySig(self, sig, txHash, pubK):
        scalar1 = ((pow(sig[1], self.n - 2, self.n) * int(txHash, 16)) % self.n)
        scalar2 = ((pow(sig[1], self.n - 2, self.n) * sig[0]) % self.n)
        point1 = self.multiplyPoint(self.G, scalar1)
        point2 = self.multiplyPoint(pubK, scalar2)
        P = self.addPoint(point1, point2)
        if P[0] == sig[0]:
            return True
        return False
