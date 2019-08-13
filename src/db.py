import os
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger

__all__ = [
    'Column',
    'Integer',
    'String',
    'Text',
    'DateTime',
    'BigInteger'
]

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
Model = declarative_base()
