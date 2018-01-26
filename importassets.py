from argparse import ArgumentParser
from itertools import chain
from datetime import datetime
from statistics import median
from math import fabs


from bitshares import BitShares
from bitshares.asset import Asset
from bitshares.witness import Witnesses, Witness
from bitshares.account import Account
from bitshares.blockchain import Blockchain

from db import engine, db, execsql, BTSAsset
from btsassetwarns import FeedWarning, ProductionWarning


class BlockchainDB:

    bts = BitShares()

    median_diff_alert = 3 #alert when this percentage varies from the median price
    block_interval = None #3 # seconds, set to None to get automatically
    witnesses = None #21 #set to None to get automatically

    # for how many rounds of last block creation a witness can go before sending a warning
    shuffle_rounds_alert = 2 


    @staticmethod
    def get_assets(codes=["USD"]):
        """  Run periodically to get data """
        for code in codes:
            producers = Asset(code)
            for feed in producers.feeds:
                dbBTS = BTSAsset(code, 
                                 datetime.now(),
                                 feed["producer"]["id"], 
                                 float(repr(feed["settlement_price"]).split(" ")[0]), 
                                 feed["maximum_short_squeeze_ratio"], 
                                 feed["maintenance_collateral_ratio"], 
                                 float(repr(feed["core_exchange_rate"]).split(" ")[0]), 
                                 feed["date"])

                db.add(dbBTS)

        db.commit()

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
        r = BlockchainDB.get_last_prices(asset)
        return median(r)

    @staticmethod
    def get_variance_of(producers="ALL", asset="USD"):
        """  get the percentage increase or decrease from the median price across all producer
             of the last stored feeds from one, many or all producers
        """
        if producers == "ALL":
            prods = BlockchainDB.get_all_producers()
        else:
            prods = producers

        r = execsql("select prices.producer, prices.sp from bts_asset as prices "
                    "inner join (select max(timestamp) ts, producer from bts_asset group by producer, asset) last "
                    "on prices.producer = last.producer "
                    "and prices.timestamp = last.ts "
                    "where prices.producer in ({})".format(",".join(map(repr, prods))))

        medval = BlockchainDB.get_last_median()

        #remove after testing
        # for prod,price in r:
        #     print("{}: {}%".format(prod, BlockchainDB.get_variance(medval, price)))

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

        for bl in btschain.blocks(currblock - startblock, currblock):
            #remove after testing
            print("{}:{}:{}".format(bl['witness'],datetime.fromtimestamp(btschain.block_timestamp(bl)), witness_id))
            if bl['witness'] == witness_id:
                block_created = True

        return block_created


    def get_witness_ids(self, name):
        """ returns witness id and witness account ids from a username  """
        w = Witness(name, bitshares_instance=self.bts)
        return w['id'], w.account['id']


    def price_out_range(self, producer, asset="USD"):
        """ returns true if there is a given percentage increase from the median of all last stored price feeds """

        prod_,price = BlockchainDB.get_variance_of([producer], asset)[0]
        #remove after testing
        print("{}:{}".format(prod_, price))
        return price > self.median_diff_alert

    def check_producer(self, producer, assets):

        warnings = []

        wit_id, acc_id = self.get_witness_ids(producer)

        for asset in assets:
            if self.price_out_range(acc_id, asset):
                warnings.append(FeedWarning())

            if not self.recent_block_creation(wit_id):
                warnings.append(ProductionWarning())

        #remove after test
        print(warnings)
        return warnings



if __name__ == '__main__':
    bdb = BlockchainDB()
    bdb.check_producer("elmato", ["USD"])

    # TODO ARGUMENT PARSING to get warnings or set cronjob
    #bdb.check_producer()

