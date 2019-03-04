from datetime import datetime
from flask import Flask, render_template, url_for, flash, redirect, jsonify, request
from forms import RegisterNodeForm, SendToForm, MiningForm, RefreshBalance, GetBlockForm, FindTxForm
from uuid import uuid4

import Blockchain as BC
import Nodes as nd

app = Flask(__name__)
app.config['SECRET_KEY'] = '21abd0726f96d981e34943401c8a0089'



node_name = str(uuid4()).replace('-', '')

blockchain = BC.Blockchain(10)

me = None
balance = 0
actN = 'None'
pkhs = []

def sendTransaction(amount, to_pubKeyH, txfee):
    global me

    if me == None:
        return 'Error, no account found', 400

    tx = me.sendTransaction(amount, to_pubKeyH, txfee)

    nodeList = list(blockchain.getNodes())
    for node in nodeList:
        nodeType = requests.get('http://{}/type'.format(node)).json()
        if nodeType == 'Miner' or nodeType == 'Full':
            requests.post('http://{}/transaction/register'.format(node), tx.serialize())

    return 'Transaction sent.', 200


def addNodes(nodeList):
    global blockchain

    if blockchain == None:
        return 'Error, no blockchain found', 400

    currentNodes = blockchain.getNodes()
    if len(currentNodes) > 10:
        return 'More than 10 nodes already present', 200

    for node in nodeList:
        blockchain.registerNode(node)
        requests.post('http://{}/nodes/register'.format(node), {'nodes':[node_name]})
        if len(blockchain.getNodes()) > 10:
            return 'More than 10 nodes already present', 200

        newNodeList = requests.get('http://{}/nodes/get'.format(node)).json()
        for newNode in newNodeList:
            blockchain.registerNode(newNode)
            requests.post('http://{}/nodes/register'.format(newNode), {'nodes':[node_name]})
            if len(blockchain.getNodes()) > 10:
                return 'More than 10 nodes already present', 200

    return 'Nodes added', 200



@app.route("/")
@app.route("/home")
def home():
    global me
    global balance
    global actN
    global pkhs

    return render_template('home.html', keys = pkhs, bal = balance, activeN = actN, title="Hello")


@app.route("/about")
def about():
    global me
    global balance
    global actN

    return render_template('about.html', keys = pkhs, bal = balance, activeN = actN, title='About')



@app.route("/minerNode", methods=['GET', 'POST'])
def minerNode():
    global me
    global balance
    global actN
    global pkhs

    if me == None:
        me = nd.MinerNode(blockchain)
        balance = me.getWallet().getBalance()
        actN = 'Miner'
        pkhs = me.getWallet().getPubKeyHs()
    elif me.getType() != 'Miner':
        flash('You must have a Miner Node for this page to work!')
        return redirect('/home')

    connectedNodes = me.bchain.getNodes()
    form1 = RegisterNodeForm()
    form2 = SendToForm()
    form3  = MiningForm()
    form4 = RefreshBalance()
    if form1.submit1.data and form1.validate_on_submit():
        addNodes([form1.nodeAddress.data])
        flash('You have added a the node {} to your network!'.format(form.nodeAddress.data))
        return redirect('/minerNode')
    if form2.submit2.data and form2.validate_on_submit():
        sendTransaction(form2.amount.data, form2.toAddress.data, form2.txFee.data)
        flash('You have sent {} coins to the address {}!'.format(form2.amount.data, form2.toAddress.data))
        return redirect('/minerNode')
    if form3.submit3.data and form3.validate_on_submit():
        test1 = me.submitBlock()
        balance = me.getWallet().getBalance()
        flash('You have begun mining! {}'.format(test1))
        return redirect('/minerNode')
    if form4.submit4.data and form4.validate_on_submit():
        balance = me.getWallet().getBalance()
        flash('Your balance has been refreshed!')
        return redirect('/minerNode')
    return render_template('miner.html', title='Mine', nodes = connectedNodes, keys = pkhs, bal = balance, activeN = actN, reg_form = form1, send_form = form2, mine_form = form3, refresh_form = form4)


@app.route("/fullNode", methods=['GET', 'POST'])
def fullNode():
    global me
    global balance
    global actN
    global pkhs

    if me == None:
        me = nd.FullNode(blockchain)
        balance = me.getWallet().getBalance()
        actN = 'Full'
        pkhs = me.getWallet().getPubKeyHs()

    elif me.getType() != 'Full':
        flash('You must have a Full Node for this page to work!')
        return redirect('/home')

    connectedNodes = me.bchain.getNodes()
    form1 = RegisterNodeForm()
    form2 = SendToForm()
    form3 = RefreshBalance()
    if form1.submit1.data and form1.validate_on_submit():
        blockchain.registerNode(form1.nodeAddress.data)
        flash('You have added a the node {} to your network!'.format(form.nodeAddress.data))
        return redirect('/fullNode')
    if form2.submit2.data and form2.validate_on_submit():
        sendTransaction(form2.amount.data, form2.toAddress.data, form2.txFee.data)
        flash('You have sent {} coins to the address {}!'.format(form2.amount.data, form2.toAddress.data))
        return redirect('/fullNode')
    if form3.submit4.data and form3.validate_on_submit():
        balance = me.getWallet().getBalance()
        flash('Your balance has been refreshed!')
        return redirect('/fullNode')
    return render_template('full.html', title='Full', nodes = connectedNodes, keys = pkhs, activeN = actN, bal = balance, reg_form = form1, send_form = form2, refresh_form = form3)

@app.route("/spvNode", methods=['GET', 'POST'])
def spvNode():
    global balance
    global pkhs
    return render_template('spv.html', title='Login', keys = pkhs, bal = balance, form=form)

txList = []
fTxDict = {}
index = 1
@app.route("/query", methods=['GET', 'POST'])
def query():
    global balance
    global me
    global actN
    global txList
    global fTxDict
    global index

    maxHeight = 0
    coinbase = 0
    difficulty = 0
    if me == None:
        flash('You must have a Full or Miner Node for this page to work!')
        return redirect('/home')
    if actN != 'Full' and actN != 'Miner':
        flash('You must have a Full or Miner Node for this page to work!')
        return redirect('/home')
    maxHeight = me.bchain.blockNum()
    coinbase = me.bchain.getCoinbaseReward()
    difficulty = me.bchain.getTarget()

    transactions = me.bchain.getBlock(index).getTransactions()
    txList = []
    for tx in transactions:
        cb = tx.getCoinbase()
        if cb > 0:
            tempDict = {'Amount': cb, 'To': tx.getToAddress(), 'From': 'Coinbase', 'TxFee': tx.getTxFee(), 'Hash': tx.getHash()}
        else:
            tempDict = {'Amount': tx.getAmount(), 'To': tx.getToAddress(), 'From': tx.getFromAddress(), 'TxFee': tx.getTxFee(), 'Hash': tx.getHash()}
        txList.append(tempDict)

    form1 = GetBlockForm()
    form2 = FindTxForm()
    if form1.submit5.data and form1.validate_on_submit():
        index = form1.blockNum.data
        if index > maxHeight:
            index = 1
            flash('You must input an index from 1 to the height!')
            return redirect('/query')
        return redirect('/query')

    if form2.submit6.data and form2.validate_on_submit():
        foundTx = me.bchain.findTx(form2.txHash.data)
        if foundTx == None:
            flash('Transaction not found in the blockchain!')
            return redirect('/query')
        cb = foundTx.getCoinbase()
        if cb > 0:
            fTxDict = {'Amount': cb, 'To': foundTx.getToAddress(), 'From': 'Coinbase', 'TxFee': foundTx.getTxFee(), 'Hash': foundTx.getHash()}
        else:
            fTxDict = {'Amount': foundTx.getAmount(), 'To': foundTx.getToAddress(), 'From': foundTx.getFromAddress(), 'TxFee': foundTx.getTxFee(), 'Hash': foundTx.getHash()}
        return redirect('/query')
    return render_template('query.html', title='Query', blk = index, dif = difficulty, cb = coinbase, fTx = fTxDict, txs = txList, height = maxHeight, activeN = actN, bal = balance, block_form = form1, tx_form = form2)



@app.route('/type', methods=['GET'])
def getType():
    global me

    response = ''
    if me == None:
        response = 'None'
    elif me.getType() == 'Miner':
        response = 'Miner'
    elif me.getType() == 'Full':
        response = 'Full'
    elif me.getType() == 'SPV':
        response = 'SPV'

    return jsonify(response), 200



@app.route('/transaction/register', methods=['POST'])
def registerTransaction():
    global blockchain

    txInfo = request.get_json()
    required = ['outputs', 'inputs', 'to_pubkeyH', 'txfee', 'amount', 'coinbase', 'hash']
    if not all(key in txInfo for key in required):
        return 'Missing values', 400

    mp = blockchain.getMemPool()
    newNodes = blockchain.getNodes()
    tx = BC.constructSerializedTxs(txInfo)
    if not mp.findTx(tx.getHash()):
        mp.addTx(tx)
        for n in newNodes:
            requests.post('http://{}/transaction/register'.format(n), txinfo)
    return 'Transaction Registered', 200


@app.route('/nodes/get', methods=['GET'])
def getNodes():
    global blockchain
    if blockchain == None:
        return 'Error, no blockchain downloaded', 400

    response = list(blockchain.getNodes())
    return jsonify(response), 200



@app.route('/nodes/register', methods=['POST'])
def registerNodes():
    nodeInfo = request.get_json()

    nodeList = nodeInfo.get('nodes')
    if nodeList is None:
        return "Error: Valid list of nodes not provided", 400

    for node in nodeList:
        blockchain.registerNode(node)

    return 'Node added', 200


@app.route('/chain', methods=['GET'])
def getChain():
    global blockchain
    response = {
        'chain': blockchain.serialize(),
        'length': blockchain.blockNum(),
    }
    return jsonify(response), 200


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.acceptLargestChain()

    if replaced:
        nodeList = blockchain.getNodes()
        for node in nodeList:
            request.get('http://{}/consensus'.format(node))
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
