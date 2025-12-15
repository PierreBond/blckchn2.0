import json 
import sys
import hashlib
import requests 
from  cryptography.hazmat.primitives.asymmetric import ec 
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
from cryptography.hazmat.primitives import hashes 

API = "http://localhost:5000"

def sk_to_address(sk):
    vk = sk.public_key()
    vk_bytes = vk.public_bytes(
        encoding = serialization.Encoding.X962,
        format = serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(vk_bytes).hexdigest()[:16]

# cli commands
def cmd_gen():
    sk = ec.generate_private_key(ec.SECP256K1())
    with open("key.pem", "wb") as f:
        f.write(sk.private_bytes(
            encoding = serialization.Encoding.PEM,
            format = serialization.PrivateFormat.PKCS8,
            encryption_algorithm =serialization.NoEncryption()
        ))
    addr = sk_to_address(sk)
    print(f"Your address:", addr)
    print("private key saved to key.pem KEEP IT SECRET")

def cmd_balance(addr):
    resp = requests.get(f"{API}/chain").json()
    balance = 0
    for blk in resp["chain"]:
        for tx in blk["transactions"]:
            if tx["recipient"] == addr:
                balance += tx["amount"]
    print("Balance:", balance)

def cmd_send(pem_file: str, to: str, amount: int) -> None:
    with open(pem_file, "rb") as f:
        sk = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )
        if not isinstance(sk, ec.EllipticCurvePrivateKey):
            raise ValueError("Private key is not an EC key")
            
        sender = sk_to_address(sk)
        tx = {"sender": sender, "recipient": to, "amount": amount}
        tx_str = json.dumps(tx, sort_keys=True).encode()
        
        signature = sk.sign(
            tx_str, 
            ec.ECDSA(hashes.SHA256())
        )
        r, s = decode_dss_signature(signature)
        
        tx["signature"] = {
            "r": r.to_bytes(32, 'big').hex(),
            "s": s.to_bytes(32, 'big').hex()
        }
        
        # Submit the transaction
        payload = {
            "sender": sender,
            "recipient": to,
            "amount": amount,
            "signature": tx["signature"]
        }
        resp = requests.post(f"{API}/transactions", json=payload)
        print(resp.json())

def cmd_chain():
    blk = requests.get(f"{API}/chain").json()["chain"][-1]
    print(json.dumps(blk, indent=2))

# dispatcher
if __name__ == "__main__":
    if len(sys.argv) <2 :
        print("Usage: python wallet.py <command> [args]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "gen":
        cmd_gen()
    elif cmd == "balance" and len(sys.argv) ==3 :
        cmd_balance(sys.argv[2])
    elif cmd == "send" and len(sys.argv) == 5 :
        cmd_send(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif cmd == "chain":
        cmd_chain()
    else:
        print("Invalid command or args")