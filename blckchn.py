from __future__ import  annotations 
import hashlib, json, logging, threading, time , asyncio, uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse 
import requests
from flask import Flask, jsonify, request, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("mini-chain")

# domain models
@dataclass(slots=True)
class Transaction:
    sender:str
    recipient:str
    amount:int

    def dict(self)-> Dict[str, Any]:
        return asdict(self)
    
@dataclass(slots=True)
class Block:
    index:int
    timestamp:float
    transactions:List[Transaction]
    proof:int
    previous_hash:str

    def dict(self)-> Dict[str,Any]:
        return asdict(self)
    
class Blockchain:
    _initial_difficulty: int = 4
    _retarget_interval:int = 10 
    _target_block_time: int = 10

    def __init__(self) -> None:
        self.chain: List[Block] = []
        self.current_tramsactions: List[Transaction]= []
        self.nodes: set[str] = set()

        self._lock = threading.RLock()
        self._difficulty = self._initial_difficulty

        # create genesis block 
        genesis = Block(
            index =1,
            timestamp=time.time(),
            transactions=[],
            proof=100,
            previous_hash="0" * 64,
        )
        self.chain.append(genesis)
        logger.info("Genesi clock created")

    @staticmethod
    def hash(block: Block) -> str:
        block_string = json.dumps(block.dict(), sort_keys = True, separators=(",",":"))
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def _valid_proof(self, last_proof:int, proof:int) -> bool:
        guess =f"{last_proof}{proof}".encode()
        return hashlib.sha256(guess).hexdigest()[:self._difficulty] == "0" * self._difficulty
    
    def _proof_of_work(self, last_proof:int) -> int:
        proof = 0
        while not self._valid_proof(last_proof, proof):
            proof +=1
        return proof
    
    def _adjust_difficulty(self)-> None:
        if len(self.chain) % self._retarget_interval ==0 and len(self.chain) > 1:
            last = self.chain[-1]
            first = self.chain[-self._retarget_interval]
            elapsed = last.timestamp - first.timestamp
            avg = elapsed/ self._retarget_interval
            if avg < self._target_block_time * 0.75:
                self._difficulty += 1
                logger.info("Difficulty increased  to %s", self._difficulty)
            elif avg > self._target_block_time * 1.25 and self._difficulty > 1:
                self._difficulty -=1
                logger.info("Difficulty decreased to %s", self._difficulty)

    def new_block(self, proof:int, previous_hash:Optional[str] = None) -> Block:
        with self._lock:
            block = Block(
                index= len(self.chain) +1,
                timestamp= time.time(),
                transactions=self.current_tramsactions[:],
                proof= proof,
                previous_hash = previous_hash or self.hash(self.chain[-1])
            )
            self.current_tramsactions.clear()
            self.chain.append(block)
            self._adjust_difficulty()
            return block
    
    def new_transaction(self, sender:str, recipient: str, amount: int) -> int:
        if amount < 0:
            raise ValueError("Amount must be a non negative")
        tx = Transaction(sender=sender, recipient=recipient, amount=amount)
        with self._lock:
            self.current_tramsactions.append(tx)
            return self.chain[-1].index + 1 
    
    def register_node(self, address:str) -> None:
         parsed = urlparse(address)
         if not parsed:
             raise ValueError("Invalid URL")
         with self._lock:
             self.nodes.add(parsed.netloc)
             logger.info("Registered node %s", parsed.netloc)

    def valid_chain(self, chain:List[Block]) -> bool:
        if not chain:
            return False
        prev = chain[0]
        for block in chain[1:]:
            if block.previous_hash != self.hash(prev):
                return False 
            if not self._valid_proof(prev.proof, block.proof):
                return False
            prev = block 
        return True

    def resolve_conflicts(self)-> bool:
        neighbours = self.nodes
        new_chain: Optional[List[Block]] = None
        max_len = len(self.chain)

        for node in neighbours:
            try:
                resp = requests.get(f"http://{node}/chain", timeout=3)
                if resp.status_code ==200:
                    data = resp.json()
                    length = data["length"]
                    candidate = [Block(**b) for b in data ["chain"]]
                    if length > max_len and self.valid_chain(candidate):
                        max_len = length
                        new_chain = candidate
            except requests.RequestException:
                logger.warning("Unreachable node %s", node)
                continue
        if new_chain:
            with self._lock:
                self.chain = new_chain
            logger.info("Chain replaced with length %s", max_len)
            return True
        return False
    
    @property
    def last_block(self) -> Block:
        with self._lock:
            return self.chain[-1]
        
# flask web layer 
app = Flask(__name__)
node_identifier = str(uuid.uuid4()).replace("-","")
blockchain = Blockchain()

# routes

@app.route("/chain", methods=["GET"])
def full_chain()-> Response:
    chain_data = [b.dict() for b in blockchain.chain]
    return jsonify({"chain": chain_data, "length": len(chain_data)})

@app.route("/transactions/new", methods=["POST"])
def new_transaction()-> tuple[Response, int]:
    values =  request.get_json(silent=True)
    if not values:
        return jsonify({"error":"JSON body is required"}), 400
    required = {"sender", "recipient", "amount"}
    if not required.issubset(values):
        return jsonify({"error": "Missing values"}), 400
    try:
        idx = blockchain.new_transaction(
            sender=str(values["sender"]),
            recipient=str(values["recipient"]),
            amount=int(values["amount"])
        )
    except ValueError as e:
        return jsonify({"error":str(e)}), 400
    return jsonify({"message": f"Transaction will be added to Block {idx}"}), 201

@app.route("/mine", methods=["GET"])
def mine() -> tuple[Response, int]:
    last_block = blockchain.last_block
    proof = blockchain._proof_of_work(last_block.proof)

    # reward transaction
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )
    block = blockchain.new_block(proof)

    response ={
        "message":"New Block Forged", 
        "index": block.index,
        "transactions":[tx.dict() for tx in block.transactions],
        "proof": block.proof,
        "previous_hash": block.previous_hash,
    }
    return jsonify(response), 200

@app.route("nodes/register",methods =["POST"])
def register_nodes()-> tuple[Response, int]:
    values = request.get_json(silent=True)
    if not values or "nodes" not in values:
        return jsonify({"error":"Please supply a valid list of nodes"}), 400
    for node in values["nodes"]:
        try:
            blockchain.register_node(node)
        except ValueError as e:
            return jsonify({"error", str(e)}), 400
    return jsonify({"message":"New  nodes have been added", "total_nodes":list(blockchain.nodes)}), 201

@app.route("nodes/resolve", methods=["GET"])
def concensus()-> tuple[Response, int]:
    replaced = blockchain.resolve_conflicts()
    if replaced :
        return jsonify({"message":"Our chain was replaced","chain":[b.dict() for b in blockchain.chain]}), 200
    return jsonify({"message":"Our chain was authoritative","chain":[b.dict() for b in blockchain.chain]}), 200

if __name__ == "main":
    app.run(host="0.0.0.0", port= 5000 , threaded = True)