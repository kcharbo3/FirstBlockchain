import hashlib
from flask import Flask, jsonify, request
from uuid import uuid4
import requests
import EllCurveMath as ecdsa
import Blockchain as BC


        
class Wallet:
    
    def __init__(self, bc):
        self.bchain = bc
        self.crypto = ecdsa.EllCurveMath()
        self.privKeys = [self.crypto.createPrivKey()]
        self.pubKeys = [self.crypto.getPubKey(self.privKeys[0])]    
        self.balance = self.getBalance()
        
        self.addresses = [self.crypto.getAddress(self.pubKeys[0])]
        self.currentKeyIndex = 0
        self.pendingUtxos = {}
        
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
    

        

  

#IMPLEMENTS THE NODE
app = Flask(__name__)
#CREATES A NAME FOR THIS NODE
node_name = str(uuid4()).replace('-', '')

blockchain = BC.Blockchain(10)

me = FullNode(blockchain)



@app.route('/chain', methods=['GET'])
def getChain():
    response = {
        'chain': blockchain.serialize(),
        'length': blockchain.blockNum(),
    }
    return jsonify(response), 200



@app.route('/transaction/send', methods=['POST'])
def sendTransaction():
    
    txInfo = request.get_json()

    required = ['amount', 'to_pubkeyH', 'txfee']
    if not all(key in txInfo for key in required):
        return 'Missing values', 400
    
    tx = me.sendTransaction(txInfo['amount'], txInfo['to_pubkeyH'], txInfo['txfee'])
    if not tx:
        return 'Transaction not sent.', 400
    
    
    nodeList = list(blockchain.getNodes())
    for node in nodeList:
        if requests.get('http://{}/type'.format(node)).json() == "Miner":
            requests.post('http://{}/transaction/register'.format(node), tx.serialize())
        
    return 'Transaction sent.', 200        



@app.route('/nodes/register', methods=['POST'])
def registerNodes():
    nodeInfo = request.get_json()

    nodeList = nodeInfo.get('nodes')
    if nodeList is None:
        return "Error: Valid list of nodes not provided", 400

    for node in nodeList:
        blockchain.registerNode(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 200



@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.acceptLargestChain()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.serialize()
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.serialize()
        }

    return jsonify(response), 200


@app.route('/nodes/type', methods=['GET'])
def getType():
    return jsonify("Full"), 200




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
        
        
        
