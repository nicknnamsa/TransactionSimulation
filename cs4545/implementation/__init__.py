from .transaction_algorithm import *

def get_algorithm(name):
    if name== "transaction":
        return TransactionAlgorithm
    else:
        raise ValueError(f"Unknown algorithm: {name}")
