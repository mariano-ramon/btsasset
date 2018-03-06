#run with python3 -m unittest tests.tests on root dir
#add "allowed_apis" : ["witness_api", "debug_api", "network_node_api"] to user in node permissions json

import os
import sys
from datetime import datetime
currpath = os.path.abspath(os.path.join(os.path.dirname(__file__))) + "/"
sys.path.insert(0, currpath + '../btscheck')

import btsconf
btsconf.env = "TEST"
btsconf.initcfg()

from requests import get,post
from shutil import copy, rmtree
from json import loads, dumps
from unittest import TestCase, main as testmain
from subprocess import Popen
from time import sleep

from bitshares.price import Price
from bitshares.wallet import Wallet
from bitshares.asset import Asset
from bitshares.witness import Witness
from bitshares.blockchain import Blockchain

from btscheck import BTSCheck
from btsupdatefeed import get_assets
from db import execsqlb


witnessnodepath = btsconf.confs['witnessnodepath']
nodecmd, datadir = witnessnodepath + "witness_node",  witnessnodepath + "test_datadir"

walletpath = btsconf.confs['walletpath']
walletcmd = btsconf.confs['walletpath'] + "/cli_wallet"
walletpass = btsconf.confs['walletpass']
wallethttp = btsconf.confs['wallethttp']
walletfile =  "/tmp/test_wallet.json"

node = btsconf.confs['node']
chainid = btsconf.confs['chainid']

btsc = None

walletproc = None
nodeproc = None

SLEEP_INTERVAL = 6 # 6 seconds

def setup_test():

    print("setup test")
    #stop server if running
    Popen(["pkill", "--signal=SIGTERM", 'witness_node'])
    #sleep(2)

    rmtree(datadir)
    os.mkdir(datadir)

    if 'test.db' not in btsconf.confs['connstring']:
        raise Exception("wrong configuration. May delete production records. Stopped.")

    print("restarting database")
    execsqlb("delete from bts_asset")

    #btsconf.confs["bts"]. sqlDataBaseFile
    copy(currpath + "config.ini", datadir)
    copy(currpath + "wallet.json", "/tmp/test_wallet.json")
    copy(currpath + "genesis.json", "/tmp/")
    copy(currpath + "perms.json", "/tmp/")



def setup_local_wallet():
    print(btsconf.confs["bts"].wallet.created())

    if not btsconf.confs["bts"].wallet.created():
      print("creatingwallet")
      btsconf.confs["bts"].wallet.newWallet(walletpass)
      btsconf.confs["bts"].wallet.unlock(walletpass)
      btsconf.confs["bts"].wallet.addPrivateKey("5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3")

    btsconf.confs["bts"].wallet.unlock(walletpass)


def setup_wallet():

    #'{"jsonrpc": "2.0", "params": ["S8N8W4EjdE"], "method": "unlock", "id": 10}'
    payloads = ['{"jsonrpc": "2.0", "params": ["nathan", "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"], "method": "import_key", "id": 10}',
               '{"jsonrpc": "2.0", "params": ["nathan", ["5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"], true], "method": "import_balance", "id": 10}'] 

    for i in range(0,11):
        payloads.append('{"jsonrpc": "2.0", "params": ["nathan","init'+ str(i) + '","1000","BTS","",true], "method": "transfer", "id": 10}')

    for payload in payloads:
        r = post(
            "http://"+wallethttp, data=payload).json()



def publish_test_feeds():

    print(btsconf.confs["bts"].config_defaults)

    priceA = Price(0.4, base="USD", quote="BTS", bitshares_instance=btsconf.confs["bts"])
    priceB = Price(0.9, base="USD", quote="BTS", bitshares_instance=btsconf.confs["bts"])


    for i in range(0,10):
        btsconf.confs["bts"].publish_price_feed(
            "USD",
            settlement_price=priceA,
            cer=priceA,
            mssr=110,
            mcr=175,
            account="init" + str(i)
        )

    btsconf.confs["bts"].publish_price_feed(
        "USD",
        settlement_price=priceB,
        cer=priceB,
        mssr=110,
        mcr=175,
        account="init10"
    )


def start_test_node():
    proc = Popen([nodecmd, '--data-dir=' + datadir ])
    sleep(5)
    btsconf.confs["bts"].connect(btsconf.confs["bts"],**btsconf.confs["rpclogin"])

    cnt = 0
    while True:

        #c = '{"jsonrpc": "2.0", "params": ["database", "get_accounts", ["1.2.1"]], "method": "call", "id": 10}'
        c = '{"jsonrpc": "2.0", "params": ["database", "get_accounts", [["1.2.1"]]], "method": "call", "id": 10}'
        r = btsconf.confs["bts"].rpc.rpcexec(loads(c))

        if 'id' in r[0]:
            break

        if cnt == 10:
            raise Exception("test node failed starting")

        sleep(1)
        cnt += 1

    return proc, btsc



def approve_witnesses():
    btsconf.confs["bts"].approvewitness(["1.6.1","1.6.2","1.6.3","1.6.4","1.6.5","1.6.6","1.6.7","1.6.8","1.6.9","1.6.10","1.6.11"], 'nathan')
    sleep(SLEEP_INTERVAL)



def start_test_wallet():

    proc = Popen(["./cli_wallet", "--wallet-file=/tmp/test_wallet.json",
                        "--chain-id=" + chainid,
                        "--server-rpc-endpoint=" + node, 
                        "--rpc-http-endpoint="+ wallethttp], cwd=walletpath)

    sleep(2)

    cnt = 0
    while True:

        c = '{"jsonrpc": "2.0", "params": ["S8N8W4EjdE"], "method": "unlock", "id": 10}'
        r = post("http://"+wallethttp, data=c).json()

        if 'result' in r:
            break

        if cnt == 10:
            raise Exception("test wallet failed starting")

        sleep(1)
        cnt += 1

    return proc




def generate_test_blocks():
    #generar una ronda con el witness pedro, sacar a pedro, hacer dos rondas mas, chequear que pedro no genero bloques

    c = '{"jsonrpc": "2.0", "params": ["debug", "debug_generate_blocks", ["5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3", 256]], "method": "call", "id": 10}'
    r = btsconf.confs["bts"].rpc.rpcexec(loads(c))
    print(r)


def setup_env_for_testing():
    setup_test()
    global nodeproc
    global walletproc
    nodeproc, btsc = start_test_node()

    walletproc = start_test_wallet()
    setup_wallet()
    setup_local_wallet()
    approve_witnesses()
    print("Wait maitenance interval")
    sleep(SLEEP_INTERVAL)
    publish_test_feeds()
    get_assets()
    generate_test_blocks()


def terminate_processes():


    Popen(["pkill", "--signal=SIGTERM", 'witness_node'])
    Popen(["pkill", "--signal=SIGTERM", 'cli_wallet'])



# try:
#     print("setup_env_for_testing")
#     setup_env_for_testing()

#     btsc = BTSCheck()
#     btsc.bts = btsconf.confs["bts"]
#     btsc.bts.connect(btsconf.confs["bts"],**btsconf.confs["rpclogin"])

#     wit_id, acc_id = btsc.get_witness_ids("init10")

# except Exception as e:
#     print("ERROR:{}".format(e))
#     terminate_processes()
#     exit()



class TestBtsAssets(TestCase):

    # def setUp(self):
    #     pass
    # def tearDown(self):
    #     pass

    def setUpClass():
        try:
            print("setup_env_for_testing")
            setup_env_for_testing()

            global btsc
            btsc = BTSCheck()
            btsc.bts = btsconf.confs["bts"]
            btsc.bts.connect(btsconf.confs["bts"],**btsconf.confs["rpclogin"])

            

        except Exception as e:
            print("ERROR:{}".format(e))
            terminate_processes()
            exit()


    def tearDownClass():
        terminate_processes()



    def test_price_out_range(self):
        global btsc
        wit_id, acc_id = btsc.get_witness_ids("init10")
        self.assertTrue(btsc.price_out_range(acc_id))

    def test_recent_block_creation(self):
        global btsc
        wit_id, acc_id = btsc.get_witness_ids("init10")
        self.assertTrue(btsc.recent_block_creation(wit_id))


print("Testing")
testmain()


print("Terminating processes")
sleep(2)
terminate_processes()
