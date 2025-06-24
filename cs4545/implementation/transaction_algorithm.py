import time
import random
from uuid import uuid4
import json
from pybloom_live import BloomFilter

from cs4545.system.da_types import *
from cs4545.system.utxo import UTXO, Transaction, dumps_tx_list, loads_tx_list


@dataclass(msg_id=1)
class Message:
    txs_json: str


@dataclass(msg_id=2)
class TerminationMessage:
    node_id: int


class TransactionAlgorithm(DistributedAlgorithm):
    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)
        self.add_message_handler(Message, self.on_message)
        self.add_message_handler(TerminationMessage, self.on_termination_message)

        self.number_nodes = 10
        self.number_byzantine = 1

        self.ignore_nodes: set[int] = set()
        self.context_history: Dict[int, List[Tuple[str, int]]] = {}
        self.balances: Dict[int, int] = {}
        self.termination_msgs: Dict[int, int] = {i: 0 for i in range(self.number_nodes + 1)}
        self.transaction_counter = 0

        self.utxos: dict[str, UTXO] = {}
        self.tx_seen: set[str] = set()

        self.spent_bloom = BloomFilter(capacity=10000, error_rate=0.001)

    def init_genesis(self):
        for nid in range(self.number_nodes):
            utxo = UTXO("GEN", nid, 10000, owner_pk=bytes([nid]))
            self.utxos[utxo.id()] = utxo

    def mk_simple_tx(self, to_id):
        mine = next(u for u in self.utxos.values() if u.owner_pk == bytes([self.node_id]))
        out1 = UTXO(str(uuid4()), 0, mine.amount // 2, owner_pk=bytes([self.node_id]))
        out2 = UTXO(str(uuid4()), 0, mine.amount - out1.amount, owner_pk=bytes([to_id]))
        return Transaction(str(uuid4()), [mine.id()], [out1, out2], time.time())

    def flag_byzantine(self, node_id: int):
        if node_id in self.ignore_nodes:
            return
        self.ignore_nodes.add(node_id)
        self.termination_msgs[node_id] += 1

        for p in self.get_peers():
            self.ez_send(p, TerminationMessage(node_id))

        if self.termination_msgs[node_id] > self.number_byzantine:
            self.stop_execution()

    async def on_start_as_starter(self):
        self.init_genesis()
        self.start_time = time.time()
        self.ignore_nodes.add(self.node_id)

        peer_a, peer_b = random.sample(self.get_peers(), 2)
        id_a = self.node_id_from_peer(peer_a)
        id_b = self.node_id_from_peer(peer_b)

        tx_legit = self.mk_simple_tx(id_a)

        reused_input = tx_legit.inputs[0]
        tx_bad_id = str(uuid4())
        out_bad = UTXO(tx_bad_id, 0, self.utxos[reused_input].amount, owner_pk=bytes([id_b]))
        tx_double = Transaction(tx_bad_id, [reused_input], [out_bad], time.time())

        def apply_local(tx: Transaction):
            self.tx_seen.add(tx.tx_id)
            for i in tx.inputs:
                # self.spent_bloom.add(i)
                self.utxos.pop(i, None)
            for o in tx.outputs:
                self.utxos[o.id()] = o

        apply_local(tx_legit)
        apply_local(tx_double)

        self.ez_send(peer_a, Message(dumps_tx_list([tx_legit])))
        print(f"[Node {self.node_id}] Sent *legit* tx {tx_legit.tx_id[:8]}… to Node {id_a}")

        self.ez_send(peer_b, Message(dumps_tx_list([tx_double])))
        print(f"[Node {self.node_id}] Sent *double* tx {tx_double.tx_id[:8]}… to Node {id_b}")

        self.transaction_counter += 2
        await super().on_start_as_starter()

    async def on_start(self):
        self.init_genesis()
        self.start_time = time.time()

        if self.node_id == 0:
            await self.on_start_as_starter()
        else:
            await super().on_start()

    @message_wrapper(Message)
    async def on_message(self, peer: Peer, payload: Message):

        self.transaction_counter += 1

        sender_id = self.node_id_from_peer(peer)
        new_txs = loads_tx_list(payload.txs_json)

        print(f"Received message from {sender_id}")

        for tx in new_txs:
            if tx.tx_id in self.tx_seen:
                continue
            self.tx_seen.add(tx.tx_id)

            if any(i in self.spent_bloom for i in tx.inputs):
                print(f"!!! Double Spend Detected !!!")
                self.flag_byzantine(sender_id)
                return
            # if not all(i in self.utxos for i in tx.inputs):
            #     self.flag_byzantine(sender_id)
            #     return

            for i in tx.inputs:
                self.spent_bloom.add(i)
                self.utxos.pop(i, None)

            for out in tx.outputs:
                self.utxos[out.id()] = out

        if new_txs:
            for p in self.get_peers():
                self.ez_send(p, Message(dumps_tx_list(new_txs)))
                self.transaction_counter += 1

    @message_wrapper(TerminationMessage)
    async def on_termination_message(self, peer: Peer, payload: TerminationMessage):
        nid = payload.node_id
        self.ignore_nodes.add(nid)
        self.termination_msgs[nid] += 1
        if self.termination_msgs[nid] > self.number_byzantine:
            self.stop_execution()

    def serialize_context_history(self):
        serializable_history = {
            str(node_id): [[uuid, amount] for uuid, amount in transactions]
            for node_id, transactions in self.context_history.items()
        }
        return json.dumps(serializable_history)

    def deserialize_context_history(self, json_str):
        if not json_str:
            return {}
        serialized_dict = json.loads(json_str)
        return {
            int(node_id_str): [(uuid, amount) for uuid, amount in transactions]
            for node_id_str, transactions in serialized_dict.items()
        }

    def stop_execution(self):
        self.last_message_time = time.time()
        self.print_metrics()
        self.stop()

    def print_metrics(self):
        print()
        print(f'[Node {self.node_id}] Summary: ')
        print(f'    Transaction counter: {self.transaction_counter}')
        print(f'    Latency (s): {self.last_message_time - self.start_time:.2f}')

