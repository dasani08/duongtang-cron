import os
import requests
import logging
from datetime import datetime
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

"""
Logging configuration
"""
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

"""
Initialize db connection
"""
env = os.environ
SQLALCHEMY_DATABASE_URI = env.get(
    'SQLALCHEMY_DATABASE_URI',
    'mysql+pymysql://root:duongtang2019@127.0.0.1/duongtang?charset=utf8')
SQLALCHEMY_POOL_RECYCLE = env.get('SQLALCHEMY_POOL_RECYCLE', 500)


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default='')
    group = Column(String(128), nullable=False)
    expired_to = Column(Integer, nullable=False)
    status = Column(Integer, default=ACTIVE_STATUS)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)


def parse_cookie(cookie_str):
    cookies = dict()
    for cookie in cookie_str.split(';'):
        cookie = cookie.split('=', maxsplit=1)
        cookies[cookie[0].strip()] = cookie[1].strip() if len(
            cookie) > 1 else None
    return cookies


def serialize_cookie(cookie_dict):
    cookies = []
    for key, value in cookie_dict.items():
        cookies.append(f'{key}={value}')
    return ';'.join(cookies)


def refresh_cookie(cookie_str):
    request_url = 'https://myaccount.google.com/'
    r = requests.get(
        request_url,
        headers={
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36'
        })

    """
    If the cookie is not authenticated, google will response with login url
    in responsed headers, then the current cookie will be regconized
    as expired, and be set to null
    """
    location = r.headers.get('content-location')
    if location is not None and location != 'https://myaccount.google.com/':
        return None

    set_cookie_dict = parse_cookie(r.headers.get('set-cookie'))
    cookie_dict = parse_cookie(cookie_str)

    for key in set_cookie_dict.keys():
        if key in cookie_dict:
            cookie_dict[key] = set_cookie_dict[key]

    return serialize_cookie(cookie_dict)


def main():
    cookies = session.query(Config).filter_by(
        key='GMAIL_COOKIE', status=Config.ACTIVE_STATUS).all()
    for cookie in cookies:
        # Skip refreshing cookie if its value is null
        if cookie.value is None:
            continue
        LOGGER.info('Refreshing cookie for email {}'.format(cookie.group))
        refreshed_cookie = refresh_cookie(cookie.value)
        print(refreshed_cookie)
        if refreshed_cookie is None:
            LOGGER.info(
                'No refreshed cookie for email {}'.format(cookie.group))
            continue
        cookie.value = refreshed_cookie
        session.add(cookie)
    try:
        session.commit()
    except Exception as exc:
        LOGGER.info("Updating cookie failed with detail {}".format(exc))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
