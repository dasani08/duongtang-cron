import os
import logging
from time import time
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

"""
Logging configuration
"""
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
LOGGER = logging.getLogger(__name__)

"""
Initialize db connection
"""
env = os.environ
SQLALCHEMY_DATABASE_URI = env.get(
    'SQLALCHEMY_DATABASE_URI',
    'mysql+pymysql://root:duongtang2019@127.0.0.1/duongtang?charset=utf8')
SQLALCHEMY_POOL_RECYCLE = int(env.get('SQLALCHEMY_POOL_RECYCLE', 500))


# Factory method returning a db session scoped
Session = sessionmaker()
engine = create_engine(SQLALCHEMY_DATABASE_URI,
                       pool_recycle=SQLALCHEMY_POOL_RECYCLE)
Session.configure(bind=engine)
session = scoped_session(Session)


"""
SQLAlchemy model
"""
Base = declarative_base()


class Stream(Base):
    __tablename__ = 'streams'

    STATUS_CODE = {
        'ACTIVE': 200,
        'DIE': 404,
        'NOT_PERM': 401
    }

    STATUS_CODE_ACTIVE = 200
    STATUS_CODE_DIE = 404
    STATUS_CODE_NOT_PERM = 401

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(256), nullable=False)
    user_id = Column(Integer, nullable=False)
    source_type = Column(String(128), nullable=False)
    type = Column(String(128), nullable=True, default="photo")
    result = Column(Text, nullable=True)
    email = Column(String(128), nullable=True)
    expired = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True, default=200)
    created_date = Column(
        DateTime, nullable=True, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    deleted_date = Column(DateTime, nullable=True, default=None)


def execute():
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        session.query(Stream).filter(Stream.created_date <
                                     one_hour_ago).filter_by(
            result=None).delete()
        session.commit()
    except SQLAlchemyError as exc:
        LOGGER.info('Have an error when deleting streams: {}'.format(exc))
        session.rollback()


def main():
    ts = time()
    execute()
    LOGGER.info('Took {}'.format(time() - ts))


if __name__ == '__main__':
    main()
