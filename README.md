# Signing Service for Miniscript Policies

Resigner is an easy to program hot signing service for miniscript policies. It provides the following features:

- Enforce preset rules (spending conditions) on transactions.
- The service cannot initiate a transaction on its own.
- Stealing a user's key is not sufficient to steal funds.
- The user can recover funds if the service is no longer available, after a given period of time (as specified by the locking script).
- Ignore transactions that do not involve the server

The Resigner countersigns transactions (according to some rules (spending conditions), set in advance in the configuration file, for example “no more than 1 million satoshis per day”. 

## Usage

The minimum supported version of Bitcoin Core is v25.0.0. If you don't have Bitcoin Core installed on your machine yet, you can download it [here](https://bitcoincore.org/en/download/).

There's a comprehensive guide for using resigner [here](docs/guide.md)

### What happens if the service disappears?

All miniscript policies registered on the service shall contain locking conditions that allow the user’s keys (possibly in combination with some other key, that is not owned by the signing server) to spend from an UTXO after some time.

An example of this will be a miniscript such as this:  
`and_v(v:pk(key_user),or_d(pk(key_service),older(12960)))`.

This represents the conditions: key_user and key_service (Resigner) need to sign off, after waiting 12960 blocks (about 90 days), the user’s key alone is enough to sign a transaction, and therefore retrieve the funds.

## PSBT

As a means to standardise the necessary information that a signer needs in order to sign a transaction, BIP-0174 introduced the Partially Signed Bitcoin Transaction (PSBT) standard, which is an interchange format that among other things, can be used in order to handle more complex scenarios where signatures from multiple parties are involved (e.g. multi signature wallets). BIP-0340 introduces PSBTv2, with a number of improvements that incidentally are extremely convenient for hardware wallets.
When we say sign a PSBT in this document, we mean: sign all the inputs controlled by the service (Resigner), that correspond to a policy (in this case: miniscript policy language) using rules defined in the spending condition configuration.

### Signing a PSBT

A PSBT contains information about:
A transaction (which is unsigned, or not completely signed)
Each of the transaction’s inputs
Each of the transaction’s outputs
The information associated with each input and output allows, among other things, to verify if there inputs (and possibly outputs) controlled by Resigner.

Resigner needs to be connected to a bitcoin full node with rpc access (possibly running on the same machine, but not necessarily) to enable verifications necessary to sign PSBTs and enforce the spending conditions to be performed. Right now, there is only plan to implement connection through `bitcoind`.
We also rely on the wallet capabilities of `bitcoind` to create/analyse/manipulate PSBTs, register and sign descriptors, and also to access the blockchain in order to monitor transactions, and as might be required to enforce the spending conditions.
Resigner shall take on the role of a signer — finalizer and updater if necessary — of the PSBT.

### API

Resigner exposes a single `post` endpoint: `/sign_psbt`

### Spending Conditions

Spending conditions (not miniscript) are rules that would be enforced by Resigner. The rules/policies are composable, flexible and are defined in a TOML format (our configuration file format).

- Spending limits in satoshis  (per day/week/month).
- Presence of additional 2FA in the PSBT.
- Require all cosigners
- Whitelist addresses controlled by Resigner.

There is the concept of roles; for example: different rules can be applied to depending on the presence of some valid signature

### Configuration

## License

Licensed under the Apache License 2.0
