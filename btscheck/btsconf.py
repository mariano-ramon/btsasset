from configparser import ConfigParser
import os
import sys

this = sys.modules[__name__]
conf = ConfigParser()
conf.read(os.path.dirname(os.path.abspath(__file__)) + "/config.ini")
this.env = "DEFAULT"
this.confs = {} 

from itertools import cycle

from bitsharesapi.bitsharesnoderpc import BitSharesNodeRPC
from bitshares import BitShares
from bitshares.instance import set_shared_bitshares_instance


class RpcPatch(BitSharesNodeRPC):

    def __init__(self, urls, user="", password="", **kwargs):       
        self.api_id = {}
        self._request_id = 0
        if isinstance(urls, list):
            self.urls = cycle(urls)
        else:
            self.urls = cycle([urls])
        self.user = user
        self.password = password
        self.num_retries = kwargs.get("num_retries", -1)

        self.wsconnect()
        self.register_apis()
        self.chain_params = { "chain_id": kwargs.get("chainid"),
                              "core_symbol": "BTS",
                              "prefix": "BTS"}


def connect(self,
            node="",
            rpcuser="",
            rpcpassword="",
            **kwargs):
    """ Connect to BitShares network (internal use only)
    """
    if not node:
        if "node" in config:
            node = config["node"]
        else:
            raise ValueError("A BitShares node needs to be provided!")

    if not rpcuser and "rpcuser" in config:
        rpcuser = config["rpcuser"]

    if not rpcpassword and "rpcpassword" in config:
        rpcpassword = config["rpcpassword"]

    self.rpc = RpcPatch(node, rpcuser, rpcpassword, **kwargs)


def initcfg():
    print(this.env)
    for var in conf[this.env]:
        this.confs[var] = conf[this.env][var]


    if this.env == "TEST":

        this.confs["bts"] = BitShares(offline=True)
        this.confs["bts"].config_defaults = {
                                   "node": this.confs["node"],
                                   "rpcpassword": this.confs["rpcpassword"],
                                   "rpcuser": this.confs["rpcuser"],
                                   "order-expiration": 7 * 24 * 60 * 60,
                                }

        this.confs["bts"].connect = connect

        set_shared_bitshares_instance(this.confs["bts"])

        this.confs["rpclogin"]= {"node":this.confs["node"],
                                 "rpcuser":this.confs["rpcuser"],
                                 "rpcpassword":this.confs["rpcpassword"],
                                 "chainid":this.confs["chainid"]}



    if this.env == "DEFAULT":
        this.confs["bts"] = BitShares()
