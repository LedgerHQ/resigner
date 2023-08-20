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

desc = "wsh(and_v(v:pk(tpubD6NzVbkrYhZ4WVLXUV8feb3wGeDj7ifwFCprLS5mMgod52gHEhdf5eRbHLfKpK7Quev91HYkP1TzooEM9jzY331ViXWzDbeWc4hFy9QdS3R/0/*),or_d(pk(tprv8ZgxMBicQKsPcu7atsTZmCB59KA6mhFr4TyKBghM7Tqu3cNHxVD2S2KFoth2b7c9tZsD3PetrANdQ8oc5KUw3KcZr273Vgxrd1dTzyGepSG/0/*),older(12960))))#uayvvntz" # descriptor of the wallet above

change_wallet_name = "" # name of the change descriptor wallet

change_desc = "wsh(and_v(v:pk(tpubD6NzVbkrYhZ4WVLXUV8feb3wGeDj7ifwFCprLS5mMgod52gHEhdf5eRbHLfKpK7Quev91HYkP1TzooEM9jzY331ViXWzDbeWc4hFy9QdS3R/1/*),or_d(pk(tprv8ZgxMBicQKsPcu7atsTZmCB59KA6mhFr4TyKBghM7Tqu3cNHxVD2S2KFoth2b7c9tZsD3PetrANdQ8oc5KUw3KcZr273Vgxrd1dTzyGepSG/1/*),older(12960))))#acuwcxfl" # descriptor for the change wallet. This is not required, it's just used  in the tests

# This options are set by resigner and would be ignored if set
min_required_sigs = 
lock_type =  
lock_value = 
```

### Bitcoind RPC options

```
[bitcoind]
network = "regtest" # ["regtest", "mainnet"]
rpc_url = "http://127.0.0.1:18443"
bitcoind_rpc_user = ""
bitcoind_rpc_password = ""
```
