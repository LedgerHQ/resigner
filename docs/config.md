## Resigner configuration file

The configuration file is used by resigner is in the toml file format and consists of option=value entries, one per line. The configuration should have been setup before starting resigner. A comment starts with a number sign (#) and extends to the end of the line.

### Resigner specific options

This are configuration options specific to the server

```
[resigner_config]
use_servertime = true # use servertime: if not true use UTC+0. Default: True
node = "bitcoind" # only `bitcoind` is supported
```

### Wallet specific options

```
[wallet]
wallet_name = "" # name of the descriptor wallet
change_wallet_name = "" # name of the change descriptor wallet

```

### Bitcoind RPC options

```
[bitcoind]
network = "regtest" # ["regtest", "mainnet"]
rpc_url = "http://127.0.0.1:18443"
bitcoind_rpc_user = ""
bitcoind_rpc_password = ""
```
