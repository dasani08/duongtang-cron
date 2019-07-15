import os
import logging
from time import time
from datetime import datetime
import requests

from sqlalchemy.dialects.mssql import TINYINT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import load_only

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


class Config(Base):
    __tablename__ = 'configs'

    ACTIVE_STATUS = 1
    INACTIVE_STATUS = 0

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default='')
    group = Column(String(128), nullable=False)
    expired_to = Column(Integer, nullable=False)
    status = Column(Integer, default=ACTIVE_STATUS)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    expires = Column(Integer, nullable=True)
    updated_timestamp = Column(BigInteger, nullable=True)


class Stream(Base):
    __tablename__ = 'streams'

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
    created_date = Column(
        DateTime, nullable=True, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    updated_meta = Column(TINYINT, nullable=True, default=False)


def get_unix_time():
    unix_time = datetime.timestamp(datetime.now())
    unix_time = str(unix_time).replace('.', '')
    unix_time = unix_time.ljust(16, '0')
    unix_time = int(unix_time)
    return unix_time


def get_api_key():
    try:
        config = session.query(Config).filter_by(key='GDRIVE_API_KEY',
                                                 status=Config.ACTIVE_STATUS)\
            .order_by(Config.updated_timestamp.asc())\
            .options(load_only('id', 'value', 'group'))\
            .with_for_update().first()

        if config is not None:
            config.updated_timestamp = get_unix_time()
            session.add(config)
            session.commit()

        return config.value
    except SQLAlchemyError:
        session.rollback()


def get_drive_info(drive_id, api_key):
    LOGGER.info('Getting video info {}'.format(drive_id))
    url = 'https://www.googleapis.com/drive/v3/files/{}?key={}'
    url = url.format(drive_id, api_key)
    params = {
        'fields': 'id,name,mimeType,size'
    }
    req = requests.get(url, params=params, headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/72.0.3626.121'
                      'Safari/537.36'
    })

    if req.status_code != 200:
        LOGGER.info('ERROR: Getting video info with status {}'.format(
            req.status_code))
        return None

    file = req.json()
    return {
        'name': file['name'],
        'size': int(file['size'])
    }


def get_streams():
    return session.query(Stream).filter(or_(
        Stream.updated_meta==False,
        Stream.updated_meta == None
    )).limit(100).all()


def execute():
    try:
        api_key = get_api_key()
        streams = get_streams()

        for stream in streams:
            file = get_drive_info(stream.source_id, api_key)
            if file:
                stream.title = file['name']
                stream.size = file['size']
                stream.updated_meta = True
                session.add(stream)
                LOGGER.info('Updated video info: id={}, name={}, '
                            'size={}'.format(stream.source_id, stream.title,
                                             stream.size))
        session.commit()
    except Exception as exc:
        session.rollback()
        LOGGER.info('ERROR: {}'.format(str(exc)))


def main():
    ts = time()
    execute()
    LOGGER.info('Took {}'.format(time() - ts))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
