from itertools import chain
from datetime import datetime
from statistics import median

from bitshares.asset import Asset

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

engine = create_engine('sqlite:///./assets.db', echo=False)
Base = declarative_base()

Session = sessionmaker()
Session.configure(bind=engine)
db = Session()



def execsql(stmt="", **kwargs):
    plain = []
    with engine.connect() as conn:
        result = conn.execute(text(stmt), **kwargs)
        for r in result:
            plain.append(list(r))

    return plain


class BTSAsset(Base):

    __tablename__ = "bts_asset"

    id = Column(Integer, primary_key=True)
    asset = Column(String)
    timestamp = Column(DateTime)
    producer = Column(String)
    sp = Column(Float)
    mssr = Column(Integer)
    mcr = Column(Integer)
    cer = Column(Float)
    feed_date = Column(DateTime)    


    def __init__(self, asset, timestamp, producer, sp, mssr, mcr, cer, feed_date):

        self.asset = asset
        self.timestamp = timestamp
        self.producer = producer
        self.sp = sp
        self.mssr = mssr
        self.mcr = mcr
        self.cer = cer
        self.feed_date = feed_date


class BlockchainDB:

    def get_assets(self, codes=["USD"]):

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
        r = execsql("select prices.sp from bts_asset as prices "
                        "inner join (select max(timestamp) ts, producer from bts_asset group by producer, asset) last "
                        "on prices.producer = last.producer "
                        "and prices.timestamp = last.ts "
                        "where prices.asset = :asset", asset=asset)

        return list(chain(*r))

    @staticmethod
    def get_all_producers():
        r = execsql("select distinct(producer) from bts_asset")
        return list(chain(*r))


    @staticmethod
    def get_last_median(asset="USD"):
        r = BlockchainDB.get_last_prices(asset)
        return median(r)

    @staticmethod
    def get_variance_of(producers="ALL", asset="USD"):
        
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
        for prod,price in r:
            print("{}: {}%".format(prod, BlockchainDB.get_variance(medval, price)))



    @staticmethod
    def get_variance(medval,prodprice):

        variance = 0

        if medval < prodprice:
            variance = (prodprice - medval) / prodprice * 100 

        if medval > prodprice:
            variance = ((medval - prodprice) / prodprice * 100 ) * -1

        return variance


if __name__ == '__main__':
    bdb = BlockchainDB()
    # bdb.get_assets()

    #print(bdb.get_last_median())
    bdb.get_variance_of()

    # use this once to create db
    #Base.metadata.create_all(engine)