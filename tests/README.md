## Resigner functional tests

We test `resigner` on a regression testing Bitcoin network, while trying to simulate using resigner in a way a user would.

[`pytest` framework](https://docs.pytest.org/en/stable/index.html) is used for testing.


### Setting up resigner for for testing

The tests are mostly self contained, setting up the environment as required. we start having `bitcoind` installed on your computer and set up in regtest, please refer to [bitcoincore](https://bitcoincore.org/en/download/) for installation.

Then seting up the config file for resigner. The default [config file](tests/config_test.toml) can be used as a base for writing your own config files

Create a new virtual environment.
```
$ python3 -m venv venv

$ source venv/bin/activate
```
Installing the requirements
```
$ pip install -r requirements-dev.txt
```
Run
```
$ pytest
```

### Test lints

We use flake8 for lint test.

```
$ make check
```
