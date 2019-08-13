import logging
from time import time
from sqlalchemy import Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.functions import sum, max
from sqlalchemy.sql.expression import cast
from .db import session
from .models import BalanceLog, UserBalance2

"""
Logging configuration
"""
LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s: %(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def get_recent_active_users():
    try:
        query = session.query(BalanceLog).with_entities(
            BalanceLog.user_id)
        query = query.order_by(BalanceLog.transaction_timestamp.desc())
        query = query.group_by(BalanceLog.user_id)
        query = query.limit(100)
        return query.all()
    except SQLAlchemyError as err:
        logger.error("get recent active user error: {}".format(err))


def get_user_balance(user_id):
    logger.info('get user balance for user_id {}'.format(user_id))
    return session.query(UserBalance2).filter_by(
        user_id=user_id).first()


def sum_user_balance(user_id, last_id=0):
    logger.info('sum user balance for user_id {}'.format(user_id))
    return session.query(BalanceLog).with_entities(
        cast(sum(BalanceLog.balance), Integer).label('total_balance'),
        max(BalanceLog.id).label('last_id')
    ).filter(
        BalanceLog.id > last_id,
        BalanceLog.user_id == user_id
    ).first()


def update_user_balance(user_id, balance, last_id):
    logger.info('update user balance for user_id {}'.format(user_id))
    try:
        curr_balance = session.query(UserBalance2).filter_by(
            user_id=user_id).with_for_update().first()
        if curr_balance is None:
            curr_balance = UserBalance2(
                last_id=0,
                balance=0,
                user_id=user_id
            )
        curr_balance.balance = balance
        curr_balance.last_id = last_id
        session.add(curr_balance)
        session.commit()
    except SQLAlchemyError as err:
        logger.error('update user balance error {}'.format(err))
        session.rollback()


def execute():
    active_users = get_recent_active_users()
    for user in active_users:
        curr_balance = get_user_balance(user.user_id)
        last_id = 0 if curr_balance is None else curr_balance.last_id
        (new_balance, last_id) = sum_user_balance(
            user.user_id, last_id)
        if new_balance and last_id:
            update_user_balance(user.user_id, new_balance, last_id)


def main():
    ts = time()
    execute()
    logger.info('Took {}'.format(time() - ts))


if __name__ == '__main__':
    main()
