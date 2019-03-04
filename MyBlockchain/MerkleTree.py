import math
import hashlib
import binascii

class TreeNode:
    def __init__(self, h):
        self.hash = h
        self.left = None
        self.right = None
        self.parent = None
        self.twin = None



class MerkleTree:
    
    def __init__(self, tList):
        self.rootNode = None
        self.txsList = tList[:]
        self.hashedNodeDict = {}
        self.levels = self.calcLevels()
        self.implement()
   
    #IF ONLY ONE ITEM IN TXLIST, WILL DUPLICATE IT, SO LEVELS WILL BE = 2
    def calcLevels(self):
        tListLen = len(self.txsList)
        if tListLen % 2 == 1:
            tListLen = tListLen + 1
        
        lvl = math.log(tListLen, 2.0) + 1

        if lvl % 1 > 0:
            lvl = lvl + 1
        return int(lvl)
        
    def implement(self):        
        if len(self.txsList) % 2 == 1:
            self.txsList.append(self.txsList[len(self.txsList) - 1])

        leafNodes = []
        for i in range(0, len(self.txsList), 2):
            node1 = TreeNode(self.txsList[i].getHash())
            
            node2 = TreeNode(self.txsList[i + 1].getHash())
            
            node1.twin = node2
            node2.twin = node1
            
            leafNodes.append(node1)
            leafNodes.append(node2)
            
            self.hashedNodeDict[node1.hash] = node1
            self.hashedNodeDict[node2.hash] = node2


        tempList = leafNodes
        for i in range(0, len(leafNodes), 2):            

            odd = len(tempList) % 2 == 1
            tempList2 = []    
            for k in range(0, len(tempList), 2):
                if odd == True and k == len(tempList) - 1:
                    tempList.append(TreeNode(tempList[len(tempList) - 1].hash))
                    tempList[len(tempList) - 2].twin = tempList[len(tempList) - 1]
                    tempList[len(tempList) - 1].twin = tempList[len(tempList) - 2]
                
                hashable = str(int(tempList[k].hash, 16) + int(tempList[k + 1].hash, 16))
                node = TreeNode(hashlib.sha256(binascii.unhexlify(hashlib.sha256(hashable.encode('utf-8')).hexdigest())).hexdigest())
                
                node.left = tempList[k]
                tempList[k].parent = node
                
                node.right = tempList[k + 1]
                tempList[k + 1].parent = node
                
                tempList[k].twin = tempList[k + 1]
                tempList[k + 1].twin = tempList[k]
                
                if len(tempList) == 2:
                    self.rootNode = tempList[0]
                    return
                
                tempList2.append(node)
                
            tempList = tempList2
           
            
    
    #Searches through dictionary (hash table) to find transaction, then walks up finding the necessary hashes to return
    #DOES NOT INCLUDE ROOT HASH IN RETURN
    #RETURNS IN ORDER: [BOTTOM OF TREE...TOP OF TREE]
    def getMerklePath(self, tx):
        txHash = tx.getHash()
        returnList = []
        tempNode = self.hashedNodeDict[txHash]
        for num in range(self.levels - 1):
            h = tempNode.twin.hash
            returnList.append(h)
            tempNode = tempNode.parent
        return returnList
    
    def getMerkleRoot(self):
        return self.rootNode.hash
