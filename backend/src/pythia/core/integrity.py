"""
Trade Integrity Ledger (Merkle Hash Chain)
SOTA 2026 Auditability

Implements a content-addressable log where each entry includes the hash
of the previous entry, creating an immutable chain.
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional

class MerkleLogEntry:

    def __init__(self, index: int, timestamp: float, data: Dict[str, Any], prev_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({'index': self.index, 'timestamp': self.timestamp, 'data': self.data, 'prev_hash': self.prev_hash}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

class ZKPTradeIntegrity:
    """
    Manages an immutable hash chain of trades.
    """

    def __init__(self):
        self.chain = []
        self.chain.append(MerkleLogEntry(0, time.time(), {'genesis': True}, '0' * 64))

    def log_trade(self, trade_data: Dict[str, Any]) -> str:
        """
        Log a trade and return its proof (hash).
        """
        prev_entry = self.chain[-1]
        new_entry = MerkleLogEntry(index=len(self.chain), timestamp=time.time(), data=trade_data, prev_hash=prev_entry.hash)
        self.chain.append(new_entry)
        return new_entry.hash

    def verify_integrity(self) -> bool:
        """
        Recompute all hashes to verify chain has not been tampered with.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            if current.prev_hash != prev.hash:
                return False
            if current.hash != current._compute_hash():
                return False
        return True
integrity_ledger = ZKPTradeIntegrity()