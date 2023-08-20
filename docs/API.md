## REST API

A REST API is available at [http://127.0.0.1:7767](http://127.0.0.1:7767) when resigner is running.

### Endpoints

Resigner exposes a single post endpoint:
```
POST /process-psbt  `Sign a PSBT using keys held by resigner`
```
Request body
```

Content-type: "application/json"

`example`
{"psbt": ""}

```
Response
```
200 OK
Content-type: "application/json"

`example`
{"psbt":"", signed: true}
```

### Usage

```
example usage
$ ./resigner.py --config_path=tests/config_test.toml
```

```shell
curl -X POST http://localhost:7767/process-psbt -H 'Content-Type: application/json' -d '{"psbt": "cHNidP8BAH0CAAAAAf4cVtULQkZVexQefMLZ2jcRmQQs10Pr/NM1DbR6h6O/AQAAAAD/////AoCWmAAAAAAAFgAU81tMchjMEuY4Ou0nJa+Cwe0RBHRgtFYIAAAAACIAIM+eQLADIVUrkRaFuiVfzmcTnGCcQ8kJUS2mZdGxnmpOAAAAAAABAP2oAQIAAAAIi8eM3/zfUB0/VUwzl3cRe6WExI7wHYH9SXqR95q06okAAAAAAP3///8hR+lsnJFNS4Nvm8y/+0wJOAol8uclOahG3k2rymaU8gAAAAAA/f///2Ha2e5+oS4XRwLwgm5JugSYEJRzFGoQi1FKqV4XoiLSAAAAAAD9////2a6ZHInwxOUPa/nsxJ948cyC11GsFIBBEWmo9aEkhMQAAAAAAP3///8L5Ws792o+Rnd2UUWzEYHo5x+Hil3RRIpguZmfx2syWgAAAAAA/f///wHxFtCB/VG3N/qsiubQgcSQrT1bsRtTnXKymdZQnM4GAAAAAAD9////EU1tHHJamw33DmM/6Kmb2Se/g8il5qmCfAxBiJUY8boAAAAAAP3///8Njz6h8RDvi0ZrzDdcQSaiI/f7TgTbn/38eYkv3Zl8kAAAAAAA/f///wIblAIAAAAAACJRIM3mRZFYHhz+0F9x9U9cz/lVn45OthAN/hUkXKUoZgfcgNHwCAAAAAAiACBoJbtMQqvUD5EnN45XhkHYUQV2x9o3J0ovcr3huGre3sMjAAABASuA0fAIAAAAACIAIGglu0xCq9QPkSc3jleGQdhRBXbH2jcnSi9yveG4at7eIgIDtbTLItqZf4BI8rUi9KEoqAW2LC2JsH00jLofNFxTB89HMEQCID9zKxBp3Q6x4yhSGQqd4tRZdTkAnNoloT/ytN5ywlYcAiAER/izoiP/bMH/g0PtcRM3d12ZpUcUmpnMtXzvwLQP2gEBBU0hA7W0yyLamX+ASPK1IvShKKgFtiwtibB9NIy6HzRcUwfPrSEDLEcToa8Y4fFUQGiAZKmoqTmSZqZF26DRHpnwBDMW6aesc2QCoDKyaCIGAyxHE6GvGOHxVEBogGSpqKk5kmamRdug0R6Z8AQzFumnDOYUlzkAAAAAZQAAACIGA7W0yyLamX+ASPK1IvShKKgFtiwtibB9NIy6HzRcUwfPDP7Q3VsAAAAAZQAAAAAAAA=="}'
```

### Errors
