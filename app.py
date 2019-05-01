import os
import requests
import logging
import threading
import concurrent.futures
from time import time
from datetime import datetime, date, timedelta
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, Date
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
    INACTIVE_STATUS = 0

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default='')
    group = Column(String(128), nullable=False)
    expired_to = Column(Integer, nullable=False)
    status = Column(Integer, default=ACTIVE_STATUS)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    expires = Column(Date, nullable=True)


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


def get_cookie(cookie_str):

    print("[{}] Getting cookie".format(threading.current_thread().name))

    request_url = 'https://myaccount.google.com/'
    r = requests.get(
        request_url,
        headers={
            'cookie': cookie_str,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121'
            'Safari/537.36'
        })

    if r.status_code != 200:
        return None, None

    """
    If the cookie is not authenticated, google will response with login url
    in responsed headers, then the current cookie will be regconized
    as expired, and be set to null
    """
    location = r.headers.get('content-location')
    if location is not None and \
            location.strip('/') != 'https://myaccount.google.com':
        return None, None

    link = r.headers.get('link')
    if link is not None:
        return None, None

    set_cookie = r.headers.get('set-cookie')
    if set_cookie is None:
        return None, None

    set_cookie_dict = parse_cookie(set_cookie)
    cookie_dict = parse_cookie(cookie_str)
    expires = datetime.strptime(
        set_cookie_dict['expires'], '%a, %d-%b-%Y %H:%M:%S %Z')

    for key in set_cookie_dict.keys():
        if key in cookie_dict:
            cookie_dict[key] = set_cookie_dict[key]

    return (serialize_cookie(cookie_dict), expires)


def refresh_cookie(cookies):
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=None, thread_name_prefix="duongtang") as thread_pool:
        future_to_cookie = {thread_pool.submit(
            get_cookie, cookie.value): cookie.group for cookie in cookies}
        for future in concurrent.futures.as_completed(future_to_cookie):
            email = future_to_cookie[future]
            try:
                (refreshed_cookie, expires) = future.result()
            except Exception as exc:
                print('{} generated an exception: {}'.format(email, exc))
            else:
                if refreshed_cookie is None:
                    LOGGER.info(
                        'No refreshed cookie for email: {}'.format(email))
                    session.query(Config).filter_by(
                        group=email, key='GMAIL_COOKIE').update({
                            'status': Config.INACTIVE_STATUS
                        })
                else:
                    session.query(Config).filter_by(
                        group=email, key='GMAIL_COOKIE').update({
                            'value': refreshed_cookie,
                            'expires': expires.date()
                        })
                    LOGGER.info(
                        'Refreshing cookie for email {} completed'.format(
                            email))
        session.commit()


def execute_refresh():
    while True:
        PAGE_SIZE = 1000
        # curr_date = date.today()
        next_day = date.today() + timedelta(days=1)
        try:
            cookies = session.query(Config).filter_by(
                key='GMAIL_COOKIE',
                status=Config.ACTIVE_STATUS).filter(
                (Config.expires == None) | (Config.expires == next_day)
            ).limit(PAGE_SIZE).with_for_update().all()

            if len(cookies) == 0:
                raise Exception('All cookie was updated')

            refresh_cookie(cookies)
        except Exception as e:
            LOGGER.info(e)
            session.commit()
            break


def main():
    ts = time()
    execute_refresh()
    print('Took {}'.format(time() - ts))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
