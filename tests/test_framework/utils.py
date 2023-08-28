from ...src import AggregateSpends

def fund_address(address, funder, amount):
    funder.sendtoaddress(address, amount)
    funder_addr = funder.getnewaddress()
    funder.generatetoaddress(10, funder_addr)

def createpsbt(wallet, utxos, address, amount, change_address):
    fee = 0.001
    amount_available_for_spend = 0

    for utxo in utxos:
        amount_available_for_spend += utxo["amount"]

    if amount_available_for_spend < (amount+fee):
        raise ValueError("amount_available_for_spend is less than spend amount")
    
    change = round(amount_available_for_spend - amount - fee, 8)
    inputs = [
        {"txid": utxo["txid"], "vout": utxo["vout"]} for utxo in utxos
    ]
    return wallet.createpsbt(
        inputs,
        [{address: amount}, {change_address: change}]
    )

def reset_aggregate_spends():
    AggregateSpends.delete()
    AggregateSpends.insert()