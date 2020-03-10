# TanMba

developing for a computer aided moving brick arbitrage tool written in python. TanMba is currently still in beta. Pls just use simulation mode to test how profitable you trade logic between huobi and binance could be. I will explain later how to use simulation mode in Usage part.
![Trade Event](https://raw.githubusercontent.com/fatalerrortan/mba_python/f_real_transaction/readme_images/trade_event.png)
## Installation and Usage via Docker (recommend Linux and Mac)

**download container**

```bash
docker pull fatalerrortxl/tanmba_test:f_real_transaction
```
**ship container**

an example we ship a container to handle eth
```bash
docker run -it --name eth_container --network host -v host/dir/etc:/opt/app/etc fatalerrortxl/tanmba_test:f_real_transaction eth simulation testing.json
```
- /host/dir/etc: use -v argument to declare the location where you put the etc folder of the repo root dir on your machine
- --network: if running multiple containers for several crypto currencies, using bridge instead of host network
- eth: crypo currency name you want to handle 
- simulation: execution mode "simulation" OR "production"  
- testing.json: the json file that you placed in the log folder to setup your own transaction behaviour. we will explain it later

## Installation and Usage on Windows 

**download pre release** [tanmba_win_0.0.1.rar](https://github.com/fatalerrortan/mba_python/releases)

- unzip rar file 
- double click app.exe 
- tanMba will ask you to offer a crypto curreny name at first 
- and then ask you to determine the exection mode "simulation" OR "production"  

## Configuration before executing the program
**1. Connection Configuration**
you need to create a specific configuration file for each crypto curreny in the etc folder before running tanMba to handle this curreny. e.g. Creating a file named "eth.ini" before handling eth trade.

- **template to build a config file e.g. eth.ini**

```bash
[PLATFORMS]
# only this two platforms are implemented currently, others platforms are in progress
activated_platforms = HUOBI, BINANCE 

[HUOBI]
api_host = api.huobi.pro
ws_url = wss://api.huobi.pro/ws
stream = {"sub": "market.$currency_pair.depth.step0","id": ""}
access_key = xxxxx-xxxxxx-xxxxxx-xxxxxx
secret_key = xxxxxxxx-xxxxx-xxxxxx-xxxxxx
simulated_currency_amount = 42
simulated_usdt_amount = 280

[BINANCE]
api_host = https://api.binance.com
ws_url = wss://stream.binance.com:9443/ws/
stream = $currency_pair@depth20
access_key = xxxxx-xxxxxx-xxxxxx-xxxxxx
secret_key = xxxxx-xxxxxx-xxxxxx-xxxxxx
simulated_currency_amount = 42
simulated_usdt_amount = 280

[DATABASE]
redis_url = localhost
redis_port = 6379
redis_index = 0
memcached_url = localhost
memcached_port = 11211

```
- **Key attributes explanation**
	- access_key: public api key of the active platform
	- secret_key:  private api key of the active platform
	- simulated_currency_amount: fake crypto currency amount for simulation
	- simulated_usdt_amount: fake usdt amount for simulation
	- rule_file: location of file containing pre-defined trade rules

**2. Trade Logic Configuration**
Just like the "rule_file" I mentioned at the end of the last chapter. You also need to define your own trade logic for each currency you want to handle. You can use and modify my template "app/rules/testing.json" to create you own and more profitable trade logic. 
```json
{
    "eos": { // for which curreny should the rules below be activated?
        "0.0009999-0.002":{ // rule label
            "from": 0.0009999, // minimal acceptable margin 
            "to": 0.002, // maximal acceptable margin 
            "rate": 0.05 // currency trade amount = total currency amount of the both platforms * 0.05, In fact the currency trade amount will be further optimized by the program. e.g. the calculated amount is beyond the account balance etc.
        },
        "0.002-0.003":{
            "from": 0.002,
            "to": 0.003,
            "rate": 0.1
        },
        "0.003-0.004":{
            "from": 0.003,
            "to": 0.004,
            "rate": 0.3
        },
        "0.004-0.005":{
            "from": 0.004,
            "to": 0.005,
            "rate": 0.4
        },
.....................................
    },
    "eth":{
.....................................
    },
    "default":{ // this default reule will be used if the trade rule of the current currency is not defined.
        "0.00009-9999999":{
            "from": 0.00009,
            "to": 9999999,
            "rate": 0.1
        }
    }
}
```
## Logging and Analysis
**1. Logging**
Whenever you start a new run, a related logfile is generated in the app/logs/. it records all important transaction and account balance with timestamp for the current run. 
-   naming convention: {datetime}_{currency name}.log  e.g. 2020-02-14_07:30:14_eth.log

**2. Analysis**
Whenever TanMba meet a new currency, it will generate a csv file named after this new curreny in app/data/ e.g. app/data/eth.csv. TanMba collects all in Runs appeared margin of the currency contantly with cumulative frequence in that file since then. e.g. see below
```csv
margin,freq
0.0001,827.0
0.0002,729.0
0.0003,653.0
0.0004,423.0
0.0005,399.0
0.0006,394.0
0.0007,297.0
0.0008,195.0
0.0009,133.0
0.001,125.0
0.0011,135.0
0.0012,117.0
0.0013,63.0
```
## License
[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/#)
