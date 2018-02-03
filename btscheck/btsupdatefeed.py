from datetime import datetime
from bitshares import BitShares
from bitshares.asset import Asset

import btsconf
btsconf.initcfg()

from db import db, BTSAsset

def get_assets(codes=["USD"]):
    """  Run periodically to get data """
    for code in codes:
        producers = Asset(asset=code, bitshares_instance=btsconf.confs['bts'])
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


if __name__ == '__main__':
    get_assets()