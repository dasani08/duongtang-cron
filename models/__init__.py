from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseModelMixin(object):
    created_date = Column(
        DateTime, nullable=True, default=datetime.now())
    updated_date = Column(DateTime, onupdate=datetime.utcnow)
    deleted_date = Column(DateTime, nullable=True, default=None)


class Config(Base, BaseModelMixin):
    __tablename__ = 'configs'

    ACTIVE_STATUS = 1
    INACTIVE_STATUS = 0

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False, default='')
    group = Column(String(128), nullable=False)
    expired_to = Column(Integer, nullable=False)
    status = Column(Integer, default=ACTIVE_STATUS)
    updated_timestamp = Column(BigInteger, nullable=True)
