import hashlib
from flask import Flask, jsonify, request
from uuid import uuid4
import requests
from urlparse import urlparse
import EllCurveMath as ecdsa
import Blockchain as BC

#SPV NODE
        
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
        self.node = None
        
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
    
    '''
    def getBalance(self):
        utxo_list = self.updateUTXOL()
        total = 0
        for key in utxo_list:
            total += utxo_list[key].getAmount()
        return total
     '''
     
    def createInput(self, utxo, message):
        for i in range(len(self.pubKeys)):
            pkHash = self.crypto.getPubKeyHash(self.pubKeys[i])
            if pkHash == utxo.getPKHash():
                self.currentKeyIndex = i
                break
        #MESSAGE IS UTXO TXHASH+INDEX, SHOULD PROBS BE SOMETHING DIFFERENT
        sig = self.crypto.signature(self.privKeys[self.currentKeyIndex], hashlib.sha1(message).hexdigest())
        unLock = [sig, self.pubKeys[self.currentKeyIndex], hashlib.sha1(message).hexdigest()]
        return BC.Input(utxo.getHash(), unLock)
        
    #RETURNS A TRANSACTION, GETS RID OF TXS IN LIST SO CAN"T DOUBLE SPEND
    '''
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
       ''' 
    
    
    def getPKHash(self):
        return self.crypto.getPubKeyHash(self.pubKeys[self.currentKeyIndex])
        
    def registerNode(self, nodeAddress):
        #address will take form of 'http://192.168.0.5:5000'
        parsed_url = urlparse(nodeAddress)
        self.node = parsed_url.netloc





class SPVNode:
        
    def __init__(self):
        self.wallet = Wallet()
            
    def getWallet(self):
        return self.wallet
    
    def sendTransaction(self, amount, to_pubKeyH, txfee):
        tx = self.wallet.sendTransaction(amount, to_pubKeyH, txfee)
        return tx
    


  

#IMPLEMENTS THE NODE
app = Flask(__name__)
#CREATES A NAME FOR THIS NODE
node_name = str(uuid4()).replace('-', '')

me = SPVNode()





@app.route('/transaction/send', methods=['POST'])
def sendTransaction():
    
    txInfo = request.get_json()

    required = ['amount', 'to_pubKeyH', 'txfee']
    if not all(key in txInfo for key in required):
        return 'Missing values', 400
    
    tx = me.sendTransaction(txInfo['amount'], txInfo['to_pubKeyH'], txInfo['txfee'])
    if not tx:
        return 'Transaction not sent.', 400

    requests.post('http://{}/transaction/send'.format(me.wallet.node), tx.serialize())
        
    return 'Transaction sent.', 200        



#MUST BE CALLED FIRST IN ORDER TO WORK
@app.route('/nodes/register', methods=['POST'])
def registerNode():
    nodeInfo = request.get_json()

    node = nodeInfo.get('node')
    if node is None:
        return "Error: Valid list of nodes not provided", 400

    me.wallet.registerNode(node)

    response = {
        'message': 'Node has been connected',
        'node': me.wallet.node,
    }
    return jsonify(response), 200




@app.route('/nodes/type', methods=['GET'])
def getType():
    return jsonify("SPV"), 200




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
        
        
        
