import hashlib
from time import time
import collections
import requests
from urllib.parse import urlparse
import MerkleTree as MK
import EllCurveMath as ecdsa
from flask import request
import binascii



'''
Contains the classes: blockchain, block, input, output, transaction, and mempool
Uses Flask to interact with http requests and gets
'''

class Block:
    '''
    transList = the transaction list to be on the block
    dif = the difficulty it is to mine this block
    non = the nonce used in calculating the block header hash
    dex = the height of the block on the blockchain
    pHash = the header hash of the previous block
    '''
    def __init__(self, transList, dif, non, dex = 0, pHash = ''):
        self.transactionList = transList[:]
        #MIGHT CHANGE TO TXDICT
        self.difficulty = dif
        self.nonce = non
        self.index = dex
        self.previousHash = pHash
        self.timeStamp = time()
        self.merkleTree = MK.MerkleTree(self.transactionList)
        self.merkleRoot = self.merkleTree.getMerkleRoot()
        self.blockHash = self.calculateHash()
    
    def calculateHash(self):
        hashable = self.difficulty + str(self.nonce) + str(self.index) + self.previousHash + str(self.timeStamp) + self.merkleRoot
        return hashlib.sha256(hashable.encode('utf-8')).hexdigest()
    
    def getBlockSize(self):
        return len(self.transactionList)
    
    def getHeader(self):
        return self.blockHash
    
    def getTime(self):
        return self.timeStamp
    
    def getTransactions(self):
        return self.transactionList
    
    def getIndex(self):
        return self.index
    
    def merkleTree(self):
        return self.merkleTree
    
    def getPreviousHeader(self):
        return self.previousHash
    
    def getDifficulty(self):
        return self.difficulty
    
    #Must be serialized to send to another node via http requests/gets
    def serialize(self):
        serializedTxs = []
        for tx in self.transactionList:
            serializedTxs.append(tx.serialize())
        returnDict = {
                'Transactions': serializedTxs,
                'Difficulty': self.difficulty,
                'Nonce': self.nonce,
                'Index': self.index,
                'PreviousHash': self.previousHash,
                'TimeStamp': self.timeStamp,
                'Root': self.merkleRoot,
                'Hash': self.blockHash
                }
        return returnDict

    

            
            

class Blockchain:
    '''
    bSizeLimit = the max size of each block
    ch = the chain to accept and start with, useful when switching blockchains due to consensus
    mp = the mempool object, useful when switching blockchains due to consensus
    '''
    def __init__(self, bSizeLimit, ch = [], mp = None):
        self.coinbaseReward = 50
        if ch == []:
            self.chain = [self.createGenesisBlock()]
        else:
            self.chain = ch
        self.utxos = {}
        self.blockSizeLimit = bSizeLimit
        #CURRENT ONE IS VERY QUICK AND EASY
        self.target = "2003a30c"
        if mp == None:
            self.memPool = Mempool()
        else:
            self.memPool = mp
        self.nodes = ()
        
    #CHECK THIS
    def createGenesisBlock(self):        
        #MY PUBKEYHASH
        cbOutput = Output(self.coinbaseReward, "14b23e638f3abca17e920c3c75eda82d3a84d9d3", "0", 0)
        return Block([Transaction([cbOutput], [None], 0, 0, 0, self.coinbaseReward)], "0", 0)

    def getLatestBlock(self):
        return self.chain[-1]
    
    def addBlock(self, newBlock):
        if not self.validateBlock(newBlock):
            return False
        self.chain.append(newBlock)
        #Coinbase transactions are never added to mem pool
        txList = newBlock.getTransactions()
        for tx in txList:
            if not tx.isCoinbase():
                self.memPool.removeTxs([tx])
        self.updateUTXOS(newBlock.getTransactions())
        self.clearMemPool()
        
        nodeList = list(self.nodes)
        
        self.acceptLargerChain()
        for node in nodeList:
            request.get('http://{}/consensus'.format(node))
        
        self.updateCoinbaseReward()
        return True
        
        
    def changeTarget(self, newTarget):
        self.target = newTarget
        
    def validateBlock(self, block):
        if block.getBlockSize() > self.blockSizeLimit:
            return False
        if int(block.getHeader(), 16) >= self.getTargetNum():
            return False
        if block.getDifficulty != self.getTargetNum():
            return False
        #Timestamp can't be more than two hours in the future
        if block.getTime() - time() > (60 * 60 * 2):
            return False
        if not block.getTransactions()[0].isCoinbase():
            return False
        if not self.validateTransactions(block.getTransactions()):
            return False
        if block.getIndex() != len(self.chain):
            return False
        if block.getPreviousHeader() != self.getLatestBlock().getHeader():
            return False
        return True
    
    def isValid(self):
        for i in len(self.chain):
            block = self.chain[i]
            if block.getBlockSize() > self.blockSizeLimit:
                return False
            if int(block.getHeader(), 16) >= block.getDifficulty():
                return False
            if not block.getTransactions()[0].isCoinbase():
                return False
            if not self.validateTransactions(block.getTransactions()):
                return False
            if i > 0: 
                if block.getPreviousHeader() != self.chain[i - 1].getHeader():
                    return False
            return True

    
    
    def getTarget(self):
        return self.target
    
    def getBlockSize(self):
        return self.blockSizeLimit
    
    def getMemPool(self):
        return self.memPool
    
    def updateUTXOS(self, newTXs):
        for tx in newTXs:
            if not tx.isCoinbase():
                oldOutputs = tx.getOutputs()
                for o in oldOutputs:
                    self.utxos.pop(o.getIdentifier(), None)
            newOutputs = tx.getNewOutputs()
            for u in newOutputs:
                self.utxos[u.getIdentifier()] = u

    def getUTXOS(self):
        return self.utxos
    
    def blockNum(self):
        return len(self.chain)
    
    #RETURNS IN DECIMAL
    def getTargetNum(self):
        exponent = self.target[:2]
        coefficient = self.target[2:]
        return int(coefficient, 16) * (2**(8 * (int(exponent, 16) - 3)))


    def clearMemPool(self):
        txList = self.memPool.getTxList()
        for tx in txList:
            outputs = tx.getOutputs()
            inputs = tx.getInputs()
            if not tx.isCoinbase():
                if len(outputs) == 0 or len(inputs) == 0:
                    self.memPool.removeTxs([tx])
                elif tx.signTx() == False:
                    self.memPool.removeTxs([tx])
                else:
                    #make sure all outputs are utxos on the blockchain
                    for o in outputs:
                        if not o.getIdentifier() in self.getUTXOS():
                            self.memPool.removeTxs([tx])
                            break
                        
        return True    
        

    def validateTransactions(self, txList):
        totalOutputs = {}
        for tx in txList:
            outputs = tx.getOutputs()
            inputs = tx.getInputs()
            if not tx.isCoinbase():
                if len(outputs) == 0 or len(inputs) == 0:
                    return False
                if tx.signTx() == False:
                    return False
                for o in outputs:
                    #This line checks for duplicate outputs
                    if o.getIdentifier() in totalOutputs:
                        return False
                    if not o.getIdentifier() in self.getUTXOS():
                        return False
                    if self.getUTXOS().get(o.getIdentifier()).getAmount() != o.getAmount():
                        return False
                    totalOutputs[o.getIdentifier()] = o
            else:
                txAmount = 0
                txAmount = tx.getNewOutputs()[0].getAmount()
                if txAmount > self.coinbaseReward + self.getTxFees(txList):
                    return False
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
            

    def serialize(self):
        serializedBlocks = []
        for block in self.chain:
            serializedBlocks.append(block.serialize())
        returnDict = {
                'coinbaseReward': self.coinbaseReward,
                'chain': serializedBlocks,
                'blockSizeLimit': self.blockSizeLimit,
                'target': self.target,
                'memPool': self.memPool.serialize(),
                'size': self.blockNum()
                }
        return returnDict
        
    def registerNode(self, nodeAddress):
        #address will take form of 'http://192.168.0.5:5000'
        parsed_url = urlparse(nodeAddress)
        self.nodes.add(parsed_url.netloc)


    def acceptLargestChain(self):
        nodeList = list(self.nodes)
        
        maxLength = self.blockNum()
        maxChain = None
        
        for node in nodeList:
            response = requests.get('http://{}/chain'.format(node))
            if response.status_code == 200:
                #size = response.json()['size']
                #tempChain = response.json()['chain']
                tempBChain = constructSerializedChain(response.json())
                if tempBChain.blockNum() > maxLength and self.isValid(tempBChain):
                    maxLength = tempBChain.blockNum()
                    maxChain = tempBChain
        
        if maxChain:
            self.memPool = maxChain.getMemPool()
            self.chain = maxChain.chain
            self.utxos = maxChain.utxos
            return True
        
        return False

    def getNodes(self):
        return self.nodes
    
    
    def updateCoinbaseReward(self):
        num = self.blockNum() / 210,000
        newReward = 50.0
        for i in range(num):
            newReward = newReward / 2.0
        self.coinbaseReward = newReward
        
    def getCoinbaseReward(self):
        return self.coinbaseReward
        
'''

'''  
#AKA UTXO
class Output:
    #locking script is the pubkeyhash
    def __init__(self, amount, lockingScript, tHash, ind):
        self.amount = amount
        self.lockingScript = lockingScript
        self.txHash = tHash
        self.index = ind
        self.identifier = hashlib.sha256(binascii.unhexlify(self.txHash + str(self.index))).hexdigest()
    
    def getLockingScript(self):
        return self.lockingScript
    
    def getHash(self):
        return self.txHash
    
    def getIndex(self):
        return self.index
    
    def getPKHash(self):
        return self.lockingScript
    
    def getAmount(self):
        return self.amount
    
    def getIdentifier(self):
        return self.identifier
    
    def serialize(self):
        returnDict = {
                'amount': self.amount,
                'lockingScript': self.lockingScript,
                'txHash': self.txHash,
                'index': self.index,
                'identifier': self.identifier
                }
        return returnDict

class Input:
    def __init__(self, utxoHash, unlockingScript):
        self.utxo_txHash = utxoHash #references the transaction the output was a part of
        self.unlockingScript = unlockingScript #contains sig and pubKey
        
    def getUnlockingScript(self):
        return self.unlockingScript
    
    def serialize(self):
        returnDict = {
                'hash': self.utxo_txHash,
                'unlockingScript': self.unlockingScript
                }
        return returnDict
    
    
class Transaction:
    def __init__(self, outs, inps, tpkh, txf, amt, cb = 0, txHash = ''):
        self.oldOutputs = outs[:]
        self.inputs = inps[:]
        self.to_pubKeyH = tpkh
        self.txFee = txf
        self.amount = amt
        self.crypto = ecdsa.EllCurveMath()
        self.coinbase = cb
        if txHash == '':
            self.hash = hex(self.crypto.createPrivKey())[2:-1]
        else:
            self.hash = txHash
        self.newOutputs = self.getNewOutputs()

        
    def signTx(self):        
        ls = []
        uls = []
        for u in self.oldOutputs:
            ls.append(u.getLockingScript())
        for i in self.inputs:
            uls.append(i.getUnlockingScript())
        
        #genesis transaction has one output, other coinbase transactions have None
        if self.coinbase == 0:
            if len(ls) != len(uls):
                return False
        for l, u in zip(ls, uls):
            newPubKHash = self.crypto.getPubKeyHash(u[1])
            if newPubKHash != l:
                return False
            if not self.crypto.verifySig(u[0], u[2], u[1]):
                return False
        return True

        
    def isValid(self):
        if(self.isCoinbase()):
            return True        
        if self.signTx() == False:
            return False
        if len(self.oldOutputs) == 0 or len(self.inputs) == 0:
            return False
        total = 0
        for o in self.oldOutputs:
            total = total + o.getAmount()
        if total < self.txFee + self.amount:
            return False
        return True
        
    
    def getCoinbase(self):
        return self.coinbase
    

    #REFUNDS GO TO FIRST OUTPUT IN OLDOUTPUT LIST
    def getNewOutputs(self):
        if self.coinbase > 0:
            return [Output(self.coinbase + self.txFee, self.to_pubKeyH, self.getHash(), 0)]
        newAmount = 0
        for o in self.oldOutputs:
            newAmount = newAmount + o.getAmount()
        newAmount = newAmount - self.txFee
        refund = newAmount - self.amount
        newLockScript = self.to_pubKeyH
        refundLockScript = self.oldOutputs[0].getPKHash()
        newOutput = Output(self.amount, newLockScript, hex(self.crypto.createPrivKey())[2:-1], 0)
        refundOutput = Output(refund, refundLockScript, hex(self.crypto.createPrivKey())[2:-1], 1)
        return [newOutput, refundOutput]
    

    def getHash(self):
        #hashable = json.dumps(self.utxos, self.inputs, self.to_pubKeyH).encode()
        #return hashlib.sha256(hashlib.sha256(hashable).hexdigest()).hexdigest()
        return self.hash
        
    def getInputs(self):
        return self.inputs
    
    def getOutputs(self):
        return self.oldOutputs
    
    def getTxFee(self):
        return self.txFee
    
    def getAmount(self):
        return self.amount
    
    def serialize(self):
        serializedOutputs = []
        if self.oldOutputs == [None]:
            serializedOutputs.append("None")
        else:
            for o in self.oldOutputs:
                serializedOutputs.append(o.serialize())
        serializedInputs = []
        if self.inputs == [None]:
            serializedInputs.append("None")
        else:
            for i in self.inputs:
                serializedInputs.append(i.serialize())
        returnDict = {
                'outputs': serializedOutputs,
                'inputs': serializedInputs,
                'to_pubkeyH': self.to_pubKeyH,
                'txfee': self.txFee,
                'amount': self.amount,
                'coinbase': self.coinbase,
                'hash': self.hash
                }
        return returnDict
    




    
        
#INVALID TRANSACTIONS ARE CLEARED BY BLOCKCHAIN EVERY BLOCK
class Mempool:
    
    def __init__(self, txd = {}):
        if txd == {}:
            self.txDict = {}
        else:
            self.txDict = txd
        
    def getTxDict(self):
        return self.txDict
    
    def getTxList(self):
        txs = []
        txDict = {}
        for key in self.txDict:
            tx = self.txDict[key]
            txfee = tx.getTxFee()
            if not txfee in txDict:
                txDict[txfee] = [tx]
            else:
                txDict[txfee].append(tx)

        orderedDict = collections.OrderedDict(sorted(txDict.items(), key=lambda t: t[0], reverse = True))
        
        
        for key in orderedDict:
            for tx in orderedDict[key]:
                txs.append(tx)
        return txs
    
    def removeTxs(self, txs):
        for tx in txs:
            self.txDict.pop(tx.getHash(), None)
            
    def addTx(self, tx):
        if not tx.getHash() in self.txDict:
            self.txDict[tx.getHash()] = tx
            return True
        return False
        
    def serialize(self):
        return self.txDict





def constructSerializedOutputs(sOutputs):
    returnList = []
    for sO in sOutputs:
        returnList.append(Output(sO['amount'], sO['lockingScript'], sO['txHash'], sO['index'], sO['identifier']))
    return returnList  

def constructSerializedInputs(sInputs):
    returnList = []
    for sI in sInputs:
        returnList.append(Input(sI['hash'], sI['unlockingScript']))
    return returnList


    
def constructSerializedTxs(sTxs):
    returnList = []
    for tx in sTxs:
        if tx['outputs'] == "None":
            outputs = [None]
        if tx['inputs'] == "None":
            inputs = [None]
        outputs = constructSerializedOutputs(tx['outputs'])
        inputs = constructSerializedInputs(tx['inputs'])
        returnList.append(Transaction(outputs, inputs, tx['to_pubkeyH'], tx['txfee'], tx['amount'], tx['coinbase'], tx['hash']))
    return returnList


def constructSerializedBlocks(sBlocks):
    returnList = []
    for block in  sBlocks:
        txs = constructSerializedTxs(block['Transactions'])
        returnList.append(Block(txs, block['Difficulty'], block['Nonce'], block['Index'], block['PreviousHash'], block['TimeStamp']))
    return returnList



def constructSerializedChain(chain):
    chainList = []
    for block in chain['chain']:
        chainList.append(constructSerializedBlocks(block))
    
    return Blockchain(chain['blockSizeLimit'], chainList, Mempool(chain['memPool']))
  