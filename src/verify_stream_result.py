import os
import logging
from time import time
from datetime import datetime
import requests

from sqlalchemy.dialects.mssql import TINYINT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

"""
Logging configuration
"""
LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
LOGGER = logging.getLogger(__name__)

"""
Initialize db connection
"""
env = os.environ
SQLALCHEMY_DATABASE_URI = env.get(
    "SQLALCHEMY_DATABASE_URI",
    "mysql+pymysql://root:duongtang2019@127.0.0.1/duongtang?charset=utf8",
)
SQLALCHEMY_POOL_RECYCLE = int(env.get("SQLALCHEMY_POOL_RECYCLE", 500))
MAX_UPDATED_STREAM = int(env.get("MAX_UPDATED_STREAM", 100))

headers = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/73.0.3683.86 Safari/537.36"
    )
}

# Factory method returning a db session scoped
Session = sessionmaker()
engine = create_engine(
    SQLALCHEMY_DATABASE_URI, pool_recycle=SQLALCHEMY_POOL_RECYCLE
)
Session.configure(bind=engine)
session = scoped_session(Session)

"""
SQLAlchemy model
"""
Base = declarative_base()


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(256), nullable=False)
    user_id = Column(Integer, nullable=False)
    source_type = Column(String(128), nullable=False)
    type = Column(String(128), nullable=True, default="photo")
    result = Column(Text, nullable=True)
    email = Column(String(128), nullable=True)
    title = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True, default=200)
    created_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    updated_meta = Column(TINYINT, nullable=True, default=False)


def get_streams():
    return (
        session.query(Stream)
        .filter(Stream.status_code == 403)
        .limit(300)
        .all()
    )


def get_status_code(url):
    res = requests.head(url, headers=headers, timeout=30)
    return res.status_code


def execute():
    try:
        streams = get_streams()
        for stream in streams:
            status_code = get_status_code(stream.result)
            if status_code in [200, 302]:
                stream.status_code = 200
                session.add(stream)
                LOGGER.info("{}: is 200".format(stream.source_id))
            elif status_code == 404:
                session.delete(stream)
                LOGGER.info("{}: is 404".format(stream.source_id))
            elif status_code == 403:
                LOGGER.info("{}: is 403".format(stream.source_id))
        session.commit()
    except Exception as exc:
        session.rollback()
        LOGGER.info("ERROR: {}".format(str(exc)))


def main():
    ts = time()
    execute()
    LOGGER.info("Took {}".format(time() - ts))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
