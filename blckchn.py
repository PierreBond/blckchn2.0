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
        new.chain: Optional[List[Block]] =none
        max_len = len(self.chain)

        for node in neighbours: