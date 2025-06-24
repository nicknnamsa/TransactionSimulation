from dataclasses import dataclass
from typing import List
import json, base64, time

@dataclass
class UTXO:
    tx_id: str
    index: int
    amount: int
    owner_pk: bytes

    def id(self) -> str:
        return f"{self.tx_id}:{self.index}"

    def to_json(self):
        return {
            "tx_id": self.tx_id,
            "index": self.index,
            "amount": self.amount,
            "owner_pk": base64.b64encode(self.owner_pk).decode()
        }

    @staticmethod
    def from_json(d):
        return UTXO(
            d["tx_id"], d["index"], d["amount"],
            base64.b64decode(d["owner_pk"])
        )

@dataclass
class Transaction:
    tx_id: str
    inputs: List[str]
    outputs: List[UTXO]
    ts: float

    def to_json(self):
        return {
            "tx_id": self.tx_id,
            "inputs": self.inputs,
            "outputs": [o.to_json() for o in self.outputs],
            "ts": self.ts
        }

    @staticmethod
    def from_json(d):
        return Transaction(
            d["tx_id"],
            d["inputs"],
            [UTXO.from_json(o) for o in d["outputs"]],
            d["ts"]
        )

def dumps_tx_list(txs):
    return json.dumps([tx.to_json() for tx in txs])

def loads_tx_list(s):
    return [Transaction.from_json(d) for d in json.loads(s)]
