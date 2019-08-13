from datetime import datetime
from . import db


class Config(db.Model):
    __tablename__ = 'configs'

    ACTIVE_STATUS = 1
    INACTIVE_STATUS = 0

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), nullable=False)
    value = db.Column(db.Text, nullable=False, default='')
    group = db.Column(db.String(128), nullable=False)
    expired_to = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, default=ACTIVE_STATUS)
    expires = db.Column(db.Integer, nullable=True)
    updated_date = db.Column(db.DateTime, onupdate=datetime.utcnow)


class BalanceLog(db.Model):
    __tablename__ = 'balance_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    transaction_timestamp = db.Column(db.BigInteger, nullable=False)
    balance = db.Column(db.Integer, nullable=True, default=0)
    transaction_type = db.Column(db.String(32), nullable=True, default='VIEW')
    source_id = db.Column(db.String(255), nullable=True)


class UserBalance2(db.Model):
    __tablename__ = 'user_balance_2'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Integer, nullable=True, default=0)
    last_id = db.Column(db.Integer, nullable=False)
    created_date = db.Column(db.DateTime, nullable=True,
                             default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, onupdate=datetime.utcnow)
