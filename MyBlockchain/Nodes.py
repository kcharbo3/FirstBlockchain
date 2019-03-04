import hashlib
import requests
import EllCurveMath as ecdsa
import Blockchain as BC

'''
fix time of blocks every 10 min
'''


class Wallet:

    #NEEDS ACCESS TO BLOCKCHAIN SOMEHOW????
    def __init__(self, bc):
        self.bchain = bc
        self.crypto = ecdsa.EllCurveMath()
        self.privKeys = [self.crypto.createPrivKey()]
        self.pubKeys = [self.crypto.getPubKey(self.privKeys[0])]
        self.balance = self.getBalance()

        self.addresses = [self.crypto.getAddress(self.pubKeys[0])]
        self.currentKeyIndex = 0
        self.pendingUtxos = {}

    def getPubKeys(self):
        return self.pubKeys

    def getPubKeyHs(self):
        pkhs = []
        for k in self.pubKeys:
            pkhs.append(self.crypto.getPubKeyHash(k))
        return pkhs

    def addKeyPair(self):
        newKey = self.crypto.createPrivKey()
        self.privKeys.append(newKey)
        newPubK = self.crypto.getPubKey(newKey)
        self.pubKeys.append(newPubK)
        self.addresses = [self.crypto.getAddress(newPubK)]

    def switchKey(self, index):
        if index >= len(self.privKeys):
            return
        self.currentKeyIndex = index


    def getBalance(self):
        utxo_list = self.updateUTXOL()

        total = 0
        for key in utxo_list:
            total += utxo_list[key].getAmount()
        return total

    def createInput(self, utxo, message):
        for i in range(len(self.pubKeys)):
            pkHash = self.crypto.getPubKeyHash(self.pubKeys[i])
            if pkHash == utxo.getPKHash():
                self.currentKeyIndex = i
                break
        #MESSAGE IS UTXO TXHASH+INDEX, SHOULD PROBS BE SOMETHING DIFFERENT
        sig = self.crypto.signature(self.privKeys[self.currentKeyIndex], hashlib.sha1(message.encode('utf-8')).hexdigest())
        unLock = [sig, self.pubKeys[self.currentKeyIndex], hashlib.sha1(message.encode('utf-8')).hexdigest()]
        return BC.Input(utxo.getHash(), unLock)

    #RETURNS A TRANSACTION, GETS RID OF TXS IN LIST SO CAN"T DOUBLE SPEND
    def sendTransaction(self, amt, to_pubKeyH, txfee):
        utxo_list = self.updateUTXOL()

        badKeys = [key for key in self.pendingUtxos if self.pendingUtxos[key] + 2 < self.bchain.blockNum()]
        for badKey in badKeys: del self.pendingUtxos[badKey]

        #NOT SURE WHAT IT IS IN BITCOIN
        total = amt + txfee
        message = to_pubKeyH + str(total)
        utxos = []
        num = 0
        for key in utxo_list:
            if not key in self.pendingUtxos:
                utxos.append(utxo_list[key])
                num = num + utxo_list[key].getAmount()
                self.pendingUtxos[key] = self.bchain.blockNum()
                if num >= total:
                    break

        if num < total:
            return None
        inputs = []
        for i in utxos:
            inputs.append(self.createInput(i, message))

        tx = BC.Transaction(utxos, inputs, to_pubKeyH, txfee, amt)

        return tx

    def updateUTXOL(self):
        utxo_list = {}
        allutxos = self.bchain.getUTXOS()
        for pk in self.pubKeys:
            for u in allutxos:
                if allutxos[u].getPKHash() == self.crypto.getPubKeyHash(pk):
                    #works because both dictionaries use same keys
                    utxo_list[u] = allutxos[u]
        return utxo_list

    def getPKHash(self):
        return self.crypto.getPubKeyHash(self.pubKeys[self.currentKeyIndex])
    #def updateBalance(self):
        #scans blockchain for utxos with pubk of this wallet


class Node:

    def __init__(self, bc):
        self.bchain = bc
        self.wallet = Wallet(bc)

    def getWallet(self):
        return self.wallet

    def sendTransaction(self, amount, to_pubKeyH, txfee):
        tx = self.wallet.sendTransaction(amount, to_pubKeyH, txfee)
        if tx == None:
            return None
        self.bchain.getMemPool().addTx(tx)
        return tx


class MinerNode(Node):
    #SHOULD HAVE SEND TRANSACTION FUNCTION THAT GETS TRANSACTION FROM WALLET THEN SUBMITS TO MEMPOOL
    #runs computations to guess a number
    def __init__(self, bc):
        Node.__init__(self, bc)

        self.mp = self.bchain.getMemPool()

    #WONT WORK IF TRANSACTIONS ARE BAD, BUT SHOULD BECAUSE GETTRANSACTIONS ALREADY CHECKS FOR THAT
    #index must be below allowed blocksize
    #TRANSACTIONS ARE VERIFIED IN GETTRANSACTION FUNCTION AS WELL (SINGLE though so it can't catch double spending)
    def submitBlock(self, index = 10):
        txList = self.getTransactionList(index)
        txfees = self.getTxFees(txList)
        transactions = [BC.Transaction([None], [None], self.wallet.getPKHash(), txfees, 0, self.bchain.getCoinbaseReward())]
        transactions.extend(txList)

        if not self.verifyTransactions(transactions):
            return False

        for i in range(9223372036854775807):
            #MIGHT CHANGE TO TXDICT
            block = BC.Block(transactions, self.bchain.getTarget(), i, self.bchain.blockNum(), self.bchain.getLatestBlock().getHeader())
            if int(block.getHeader(), 16) < self.bchain.getTargetNum():
                if self.bchain.addBlock(block):
                    return True
                return False
        return False

    #SHOULD ORDER BY HIGHEST TX FEES AND GOOD TRANSACTIONS
    #get a transacitonlist of the first index transactions in the mempool
    #FILTERS OUT NOT VERIFIED TRANSACTIONS
    def getTransactionList(self, index):
        li = self.mp.getTxList()
        length = 0
        returnList = []

        for tx in li:
            if length == index:
                break
            if self.verifyTransactions([tx]):
                returnList.append(tx)
                length = length + 1
        return returnList



    #VERIFY TRANSACTIONS NOT YET ON THE BLOCKCHAIN
    #should gather list of outputs referenced, then look them up on blockchain and validate them
    def verifyTransactions(self, txList):
        totalOutputs = {}
        for tx in txList:
            outputs = tx.getOutputs()
            inputs = tx.getInputs()
            if not tx.isCoinbase():
                if len(outputs) == 0 or len(inputs) == 0:
                    return False
                if tx.signTx() == False:
                    return False
                #make sure all outputs are utxos on the blockchain
                for o in outputs:
                    if o.getIdentifier() in totalOutputs:
                        return False
                    if not o.getIdentifier() in self.bchain.getUTXOS():
                        return False
                    if self.bchain.getUTXOS().get(o.getIdentifier()).getAmount() != o.getAmount():
                        return False
                    totalOutputs[o.getIdentifier()] = o
        return True






    def getTxFees(self, txList):
        returnVal = 0
        for tx in txList:
            if not tx.isCoinbase():
                oldOutputs = tx.getOutputs()
                newOutputs = tx.getNewOutputs()
                txTotal = 0
                for o in oldOutputs:
                    txTotal = txTotal + o.getAmount()
                newAmount = 0
                for n in newOutputs:
                    newAmount = newAmount + n.getAmount()
                returnVal = returnVal + (txTotal - newAmount)
        return returnVal

    def getType(self):
        return 'Miner'


class FullNode:

    def __init__(self, bc):
        self.bchain = bc
        self.wallet = Wallet(bc)

    #def validateBlock(self):

    def getWallet(self):
        return self.wallet

    def sendTransaction(self, amount, to_pubKeyH, txfee):
        tx = self.wallet.sendTransaction(amount, to_pubKeyH, txfee)
        if tx == None:
            return None
        self.bchain.getMemPool().addTx(tx)
        return tx

    def getType(self):
        return 'Full'

class SPVNode:

    def __init__(self):
        self.wallet = Wallet()

    def getWallet(self):
        return self.wallet

    def sendTransaction(self, amount, to_pubKeyH, txfee):
        tx = self.wallet.sendTransaction(amount, to_pubKeyH, txfee)
        return tx

    def getType():
        return 'SPV'
