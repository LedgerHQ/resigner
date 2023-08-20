# Signing Service for Miniscript Policies

Resigner is an easy to program hot signing service for miniscript policies. It provides the following features:

- Enforce preset rules (spending conditions) on transactions.
- The service cannot initiate a transaction on its own.
- Stealing a user's key is not sufficient to steal funds.
- The user can recover funds if the service is no longer available, after a given period of time (as specified by the locking script).
- Ignore transactions that do not involve the server

The Resigner countersigns transactions (according to some rules (spending conditions), set in advance in the configuration file, for example “no more than 1 million satoshis per day”. 

#### What happens if the service disappears?

All miniscript policies registered on the service shall contain locking conditions that allow the user’s keys (possibly in combination with some other key, that is not owned by the signing server) to spend from an UTXO after some time.

An example of this will be a miniscript such as this:  
`and_v(v:pk(key_user),or_d(pk(key_service),older(12960)))`.

This represents the conditions: key_user and key_service (Resigner) need to sign off, after waiting 12960 blocks (about 90 days), the user’s key alone is enough to sign a transaction, and therefore retrieve the funds.

### Usage

Resigner needs to be connected to a bitcoin full node with rpc access (possibly running on the same machine, but not necessarily) to enable verifications necessary to sign PSBTs and enforce the spending conditions to be performed. Right now, there is only plan to implement connection through `bitcoind`.

We also rely on the wallet capabilities of `bitcoind` to create/analyse/manipulate PSBTs, register and sign descriptors, and also to access the blockchain in order to monitor transactions, and as might be required to enforce the spending conditions.
Resigner shall take on the role of a signer — finalizer and updater if necessary — of the PSBT.

The minimum supported version of Bitcoin Core is v25.0.0. If you don't have Bitcoin Core installed on your machine yet, you can download it [here](https://bitcoincore.org/en/download/).

There's a comprehensive guide for using resigner [here](docs/guide.md)

### API

Resigner exposes a single `post` endpoint: `/sign_psbt`. More detailed documentations can be found [here](docs/API.md)

### Spending Conditions

Spending conditions (not miniscript) are rules that would be enforced by Resigner. The rules/policies are composable, flexible and are defined in a TOML format (our configuration file format).

- Spending limits in satoshis  (per day/week/month).
- Presence of additional 2FA in the PSBT.
- Require all cosigners
- Whitelist addresses controlled by Resigner.

There is the concept of roles; for example: different rules can be applied to depending on the presence of some valid signature

The reference documentation for spending policies can be found [here](docs/spending_conditions.md)
### Configuration

Refer to the [configuration documentation](docs/config.md)

## License

Licensed under the Apache License 2.0
