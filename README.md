# First Blockchain
My first implementation of a Bitcoin inspired blockchain. It includes important features of bitcoin such as peer to peer decentralization, consensus, cryptographic keys, and proof of work.

# Usage
To begin, run myApp.py using python 3.0 and above. Then open your browser to http://0.0.0.0:5000/. This will take you to the home page of the application. Here, you can choose to start a node of three types: Miner, Full, and SPV (in progress). There is also a Query option that can be chosen once you start a node. Clicking on one of these titles will take you to the node's main page. To return to the home page, click the top left of the navigation bar on "Running Node:...". At the node's main page you can register other nodes to your network and send transactions to other addresses. If you have a miner node, you can mine blocks for rewards. Once a node has been started, you can begin querying the blockchain by returning to the home page and clicking on "Query". This will take you to the query main page where you can search for a block number or a certain transaction. The SPV node is still in progress.

Once you register a node, you have been connected to the network. In the network, once a transaction is sent from a node, that node broadcasts it to the other nodes in its network. These nodes will then broadcast that transaction to the nodes in its own network (unless it has already recieved the transaction). Once a block is mined by a miner node, it will broadcast the block to all nodes in its network. For each node that has a smaller blockchain height, it will replace its blockchain with the miner node's blockchain and then broadcast it to the nodes in its network.

# Class Descriptions
## EllCurveMath
EllCurveMath is where all of the cryptography math occurs. The module fastecdsa is imported but only used to generate private keys (random numbers). The class can use this private key to generate public keys and addresses using the same math that bitcoin core uses. Therefore, the same private key will generate the same public key and address in this class as in bitcoin core. 


## MerkleTree/TreeNode
The MerkleTree class is used to act as the merkle tree structure used in bitcoin core. It is a binary tree where each node stores the hash of the combination of its two children nodes' hashes. Each block in the blockchain stores one merkle tree. Each leaf node in the merkle tree stores the hash of a transaction in the block. The point of this merkle tree is to allow for the use of SPV (simplified payment verification) nodes. An SPV node can verify that a transaction is on the blockchain with the hash of the transaction and the merkle path from the tree. This way, the SPV node only needs a list of hashes (the transaction hash and merkle path) instead of the full block to verify a transaction.


## Blockchain
### Block
Stores a limited number of transactions in a list. Each block has a hash generated from the difficulty (the difficulty setting for mining), the nonce (used to increase ways miners can hash), the hash of the previous block, the time stamp, and the merkle root (the top node's hash in the merkle tree). 

### Blockchain
Stores the blocks in a list. The blockchain's constructor automatically generates a genesis block if a chain of blocks is not passed in. If a chain of blocks is passed in, it will just create the blockchain around those blocks. This is to help with consensus when one blockchain is found to be longer than the current one. 

Before adding a block, it must be verified. The block size must be within the limit, the block header hash must be greater than the target number (set by the difficulty), the timestamp must be within two hours in the future, the first transaction must be a coinbase transaction, the transactions must be valid, the block index must equal the current length of the chain (block index starts at 0), and the header of the previous block must equal the last block in the chain's header. 

The transactions are validated by requiring that the number of outputs equals the number of inputs, the unlocking script succesfully unlocks the locking script, and the outputs must be in the stored chain of current unspent transaction outputs held by the blockchain.

### Output
Holds the amount it's worth, the locking script, the transaction hash of the transaction it was created in, and an index used to create an identifier for the output. The identifier is a hash of the index and the transaction hash. The locking script is created in the Transaction class.

### Input
Stores the utxoHash and unlocking script. The unlocking script is created in the wallet class.

### Transaction
Stores a list of outputs, a list of inputs, the public key hash of the recipient, a transaction fee amount, an amount, a transaction hash, and coinbase amount. If the sum of outputs used to create the transaction is greater than the amount specified plus the transaction fee, the transaction will refund the left over to the sender. Contains the signTx() function that checks if the output locking scripts can be unlocked by the input unlocking scripts. The locking script associated to the new outputs is just a public key hash of the now owner.

### Mempool
The mempool stores the transactions waiting to be mined and validated on the blockchain.


## Nodes
### Wallet
The wallet class stores a copy of the blockchain, along with the list of private keys. It also keeps an updated dictionary of the balance of the private keys by summing the amount of UTXO (unspent transaction outputs) with a locking script of one of its public key hashes. The function sendTransaction() creates inputs with unlocking scripts of the signature generated from the EllCurveMath class. 

### Node
Contains a wallet with a copy of the blockchain. Is the base class for MinerNode and FullNode.

### MinerNode
MinerNode gathers a number of transactions from the mempool and groups them into the block. Then, it computes what the block header hash would be while varying the nonce. If the hash is less than the difficulty target, it will submit the block to the blockchain. The transactions are verified before being accepted from the mempool.

Using the flask module, http request and get functions are added at the end. These functions allow hosts to host a Node and interact with a blockchain. The mine() function tries mining a block. The consensus() function checks the other blockchains of the other nodes and replaces its blockchain with longest one.

### FullNode
FullNode is the same as MinerNode but has no mining functionality. It still has a copy of the blockchain.

### SPVNode (In Progress)
The SPVNode is supposed to act similarly to the FullNode but not contain a copy of the blockchain. It will verify transactions based on the merkle root and merkle path it is provided from a full or miner node in its network.

# Credit
The CSS file is from youtuber Corey Schafer. He used it in his tutorial at https://www.youtube.com/watch?v=MwZwr5Tvyxo&list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH&index=1
The file is at https://github.com/CoreyMSchafer/code_snippets/blob/master/Python/Flask_Blog/07-User-Account-Profile-Pic/flaskblog/static/main.css
