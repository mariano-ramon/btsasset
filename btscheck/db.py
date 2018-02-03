from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import btsconf
btsconf.initcfg()



print(btsconf.confs['connstring'])
engine = create_engine(btsconf.confs['connstring'], echo=False)
#engine = create_engine(, echo=False)
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


def execsqlb(stmt="", **kwargs):
    with engine.connect() as conn:
        result = conn.execute(text(stmt), **kwargs)


    return result



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


def create_database():
    Base.metadata.create_all(engine)
    