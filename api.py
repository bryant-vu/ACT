from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Query
import json
import base64

engine = create_engine('sqlite:///data/db.sqlite', convert_unicode=True, echo=False)
Base = declarative_base()
Base.metadata.reflect(engine)


class Questions(Base):
    __table__ = Base.metadata.tables['math']


session = scoped_session(sessionmaker(bind=engine))


def question_list():
    questionQuery = session.query(Questions.topic)

    questionList = [each for (each,) in questionQuery]

    return questionList


def questions(input_data):

    questionReturn = session.query(Questions.id,
                                   Questions.qStatement,
                                   Questions.a1,
                                   Questions.a2,
                                   Questions.a3,
                                   Questions.a4,
                                   Questions.a5,
                                   Questions.pic).filter(Questions.topic == input_data)

    dataDict = [{'id': each[0],
                 'statement': each[1],
                 'a1': each[2],
                 'a2': each[3],
                 'a3': each[4],
                 'a4': each[5],
                 'a5': each[6],
                 'a6': each[7]
                 } for each in questionReturn]

    return dataDict
