import os
import sys
import logging
from time import time
from datetime import datetime, timedelta

from sqlalchemy import create_engine, Column, Integer, String, DateTime, \
    BigInteger
from sqlalchemy.sql.functions import sum, count
from sqlalchemy.sql.expression import cast, or_
from sqlalchemy.orm import sessionmaker, scoped_session
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


class BalanceLog(Base):
    __tablename__ = 'balance_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    transaction_timestamp = Column(BigInteger, nullable=False)
    balance = Column(Integer, nullable=True, default=0)
    transaction_type = Column(String(32), nullable=True, default='VIEW')
    source_id = Column(String(255), nullable=True)


class ReportEarning(Base):
    __tablename__ = 'report_earning'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Integer, nullable=False)
    total_req = Column(Integer, nullable=False, default=0)
    total_earn = Column(Integer, nullable=False, default=0)
    created_date = Column(DateTime, nullable=True,
        default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)


def timestamp_range(the_date=None):
    if the_date is None:
        the_date = datetime.utcnow()
    begin_of_day = datetime(the_date.year, the_date.month, the_date.day)
    begin_of_day = datetime.timestamp(begin_of_day)
    end_of_day = begin_of_day + 86400
    begin_of_day = int(begin_of_day) * 1000000
    end_of_day = int(end_of_day) * 1000000

    return begin_of_day, end_of_day


def date_to_int(date):
    the_date = '{}{}{}'.format(date.year, str(date.month).rjust(2, '0'),
                           str(date.day).rjust(2, '0'))
    return int(the_date)


def execute(report_date):
    try:
        LOGGER.info('Gathering earning report for {}'.format(report_date))
        (start, end) = timestamp_range(report_date)

        result = session.query(BalanceLog).with_entities(
            count(BalanceLog.id).label('total_req'),
            cast((sum(BalanceLog.balance) * -1), Integer).label('total_earn')
        ).filter(
            or_(
                BalanceLog.transaction_type == 'VIEW',
                BalanceLog.transaction_type == 'UPLOAD_PHOTO'
            ),
            BalanceLog.transaction_timestamp >= start,
            BalanceLog.transaction_timestamp <= end
        ).one_or_none()

        if result is not None:
            (total_req, total_earn) = result
            the_date = date_to_int(report_date)
            report = session.query(ReportEarning).filter_by(
                date=the_date).first()

            if report is None:
                report = ReportEarning(
                    date=date_to_int(report_date),
                    total_req=total_req,
                    total_earn=total_earn
                )
            else:
                report.total_req = total_req
                report.total_earn = total_earn
            session.add(report)
            session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        LOGGER.info('Error: {}', exc)


def main():
    report_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date() if len(
        sys.argv) > 1 else \
        datetime.now().date() - timedelta(days=1)
    ts = time()
    execute(report_date)
    LOGGER.info('Took {}'.format(time()-ts))


if __name__ == '__main__':
    main()
