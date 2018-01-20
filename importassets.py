from bitshares.asset import Asset

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from json import loads

engine = create_engine('sqlite:///./assets.db', echo=True)
Base = declarative_base()

Session = sessionmaker()
Session.configure(bind=engine)
db = Session()

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


if __name__ == '__main__':
    bdb = BlockchainDB()
    bdb.get_assets()

    # use this once to create db
    #Base.metadata.create_all(engine)