import os
import json
import requests
import logging
import re
import concurrent.futures
from time import time
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base

"""
Logging configuration
"""
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
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
Exception
"""


class CookieError(Exception):
    pass


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


def utc_to_timestamp(utc):
    try:
        dt = datetime.strptime(utc, '%a, %d-%b-%Y %H:%M:%S %Z')
        return int(dt.timestamp())
    except ValueError:
        return None


def replace_utc_datetime(from_str):
    utc_datetime_re = re.compile(
        "\w{3}\,\s?\d{2}-\w{3}-\d{4}\s\d{2}:\d{2}:\d{2}\s\w{3}")
    matches = utc_datetime_re.findall(from_str)
    for match in matches:
        timestamp = utc_to_timestamp(match)
        if timestamp:
            from_str = from_str.replace(match, str(timestamp))
    return from_str


def parse_cookie(cookie_str):
    cookies = cookie_str.split(',')
    cookie_list = []
    for cookie in cookies:
        parts = cookie.split(';')
        (name, value) = parts[0].split('=', maxsplit=1)
        cookie_dict = {
            'name': name, 'value': value
        }
        for part in parts[1:]:
            part = part.split('=')
            cookie_dict[part[0].strip()] = part[1].strip() if len(
                part) > 1 else None
        cookie_list.append(cookie_dict)
    return cookie_list


def parse_cookie_to_dict(cookie_str):
    cookies = dict()
    cookie_str = cookie_str.strip(';')
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


def get_cookie(email, cookie_str):

    LOGGER.info("[{}] Requesting new cookie: {}".format(email, cookie_str))

    request_url = 'https://photos.google.com/u/0/'
    r = requests.get(
        request_url,
        headers={
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121'
            'Safari/537.36'
        })

    if r.status_code != 200:
        LOGGER.info("[{}] Request error: {}. Stopped".format(email,
                                                             r.status_code))
        return None

    """
    If the cookie is not authenticated, google will response with login url
    in responsed headers, then the current cookie will be regconized
    as expired, and be set to null
    """
    location = r.headers.get('content-location')
    if location is not None and \
            location.strip('/') != 'https://photos.google.com/u/0':
        LOGGER.info("[{}] Error location: {}".format(email, location))
        raise CookieError()

    link = r.headers.get('link')
    if link is not None:
        LOGGER.info("[{}] Error link: {}".format(email, link))
        raise CookieError()

    responded_cookie_str = r.headers.get('set-cookie')
    if responded_cookie_str is None:
        LOGGER.info("[{}] No cookie".format(email))
        raise CookieError()

    responded_cookie_str = replace_utc_datetime(responded_cookie_str)
    responded_cookie = parse_cookie(responded_cookie_str)
    cookie_dict = parse_cookie_to_dict(cookie_str)

    for cookie in responded_cookie:
        cookie_dict[cookie['name']] = cookie['value']

    LOGGER.info("[{}] New cookie: {}".format(email, serialize_cookie(
        cookie_dict)))

    return serialize_cookie(cookie_dict)


def refresh_cookie(cookies):
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=None, thread_name_prefix="duongtang") as thread_pool:
        future_to_cookie = {thread_pool.submit(
            get_cookie, cookie.group, cookie.value): cookie.group for cookie
                            in cookies}
        for future in concurrent.futures.as_completed(future_to_cookie):
            email = future_to_cookie[future]
            try:
                refreshed_cookie = future.result()
            except CookieError:
                LOGGER.info('Cookie of email {} is not valid'.format(email))
                session.query(Config).filter_by(
                    group=email, key='GMAIL_COOKIE').update({
                        'status': Config.INACTIVE_STATUS
                    })
            else:
                if refreshed_cookie is not None:
                    session.query(Config).filter_by(
                        group=email, key='GMAIL_COOKIE').update({
                            'value': refreshed_cookie
                        })
                    LOGGER.info(
                        '[{}] Refreshing cookie completed'.format(email))
        session.commit()


def execute_refresh():
    page_size = 100
    cookies = session.query(Config).filter_by(
        key='GMAIL_COOKIE').order_by(
        Config.updated_date.asc()
    ).limit(page_size).with_for_update().all()

    if len(cookies) == 0:
        LOGGER.info('All cookie was updated')
    else:
        refresh_cookie(cookies)


def main():
    ts = time()
    execute_refresh()
    LOGGER.info('Took {}'.format(time() - ts))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
