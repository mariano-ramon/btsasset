from itertools import chain
from datetime import datetime, timedelta
from statistics import median
from math import fabs
from json import loads

from bitshares import BitShares
from bitshares.witness import Witnesses, Witness
from bitshares.account import Account
from bitshares.blockchain import Blockchain

from db import execsql
from btsassetwarns import FeedWarning, ProductionWarning
from bitshares.instance import set_shared_bitshares_instance

import btsconf
btsconf.initcfg()


class BTSCheck:

    bts = btsconf.confs["bts"]

    median_diff_alert = 3 #alert when this percentage varies from the median price
    block_interval = None #3 # seconds, set to None to get automatically
    witnesses = None #21 #set to None to get automatically

    # for how many rounds of last block creation a witness can go before sending a warning
    shuffle_rounds_alert = 2 


    @staticmethod
    def get_last_prices(asset="USD"):
        """  returns a list of last obtained prices from all producers """
        r = execsql("select prices.sp from bts_asset as prices "
                        "inner join (select max(timestamp) ts, producer from bts_asset group by producer, asset) last "
                        "on prices.producer = last.producer "
                        "and prices.timestamp = last.ts "
                        "where prices.asset = :asset", asset=asset)

        return list(chain(*r))

    @staticmethod
    def get_all_producers():
        """ get all producers ever stored  """
        r = execsql("select distinct(producer) from bts_asset")
        return list(chain(*r))


    @staticmethod
    def get_last_median(asset="USD"):
        """ get the median of prices from all producer from last batch """
        r = BTSCheck.get_last_prices(asset)
        return median(r)


    @staticmethod
    def get_recent_average_price(producer,asset="USD"):
        """ get the average price of the last N feeds of a producer
        """


        fivemago = datetime.now() - timedelta(minutes=5)

        r = execsql("select count(id), avg(sp) from bts_asset where "
                    "producer = :producer and timestamp > :fiveminutesago", producer=producer, fiveminutesago=fivemago)

        return r


    @staticmethod
    def get_variance(medval,prodprice):
        """ Get the percentage increase o decrease between 2 values  """
        variance = fabs(prodprice - medval) / prodprice * 100 

        if medval > prodprice:
            variance = variance * -1

        return variance


    def get_shuffle_round_time(self):
        """ returns time in seconds of one round of block creation of every active witness """
        btschain = Blockchain()
        wits = len(Witnesses(bitshares_instance=self.bts))
        intv = btschain.chainParameters().get("block_interval")
        return wits * intv


    def recent_block_creation(self, witness_id):
        """ returns True if witness id is in the N last blocks created """
        btschain = Blockchain()
        block_created = False
        
        srt =  None
        if self.witnesses and self.block_interval:
            srt = self.witnesses * self.block_interval
        else:
            srt = self.get_shuffle_round_time()

        currblock =  btschain.get_current_block_num()
        startblock = srt * self.shuffle_rounds_alert

        c = ('{{"jsonrpc": "2.0", "params": ["database", "get_block_header_batch", '
            '[[{}]]], "method": "call", "id": 10}}'.format(",".join(str(x) for x in range(currblock - startblock, currblock))))

        r = btsconf.confs["bts"].rpc.rpcexec(loads(c))


        for bl in r:
            if bl[1] and bl[1]['witness'] == witness_id:
                block_created = True


        return block_created



    def get_witness_ids(self, name):
        """ returns witness id and witness account ids from a username  """
        w = Witness(name, bitshares_instance=self.bts)
        return w['id'], w.account['id']


    def price_out_range(self, producer, asset="USD"):
        """ returns true if there is a given percentage increase from the median of all last stored price feeds """

        is_out_range = False

        cnt,price = BTSCheck.get_recent_average_price(producer, asset)[0]
        median = self.get_last_median()
        if cnt:
            self.get_variance(median, price) > self.median_diff_alert

        return is_out_range

    def check_producer(self, producer, assets):

        warnings = []

        wit_id, acc_id = self.get_witness_ids(producer)

        for asset in assets:
            if self.price_out_range(acc_id, asset):
                warnings.append(FeedWarning())

            if not self.recent_block_creation(wit_id):
                warnings.append(ProductionWarning())

        return warnings


if __name__ == '__main__':
    bdb = BTSCheck()
    bdb.check_producer("elmato", ["USD"])
