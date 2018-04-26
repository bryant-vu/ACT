from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Query
import json

engine = create_engine('sqlite:///data/data.sqlite', convert_unicode=True, echo=False)
Base = declarative_base()
Base.metadata.reflect(engine)


class Questions(Base):
    __table__ = Base.metadata.tables['db']


session = scoped_session(sessionmaker(bind=engine))


def question_list():
    questionQuery = session.query(Questions.topic)

    questionList = [each for (each,) in questionQuery]

    return questionList


def questions(input_data):

    questionReturn = session.query(Questions.qstatement,
                                   Questions.a1,
                                   Questions.a2,
                                   Questions.a3,
                                   Questions.a4,
                                   Questions.a5).filter(Questions.topic == input_data)

    dataDict = [{'statement': each[0],
                 'a1': each[1],
                 'a2': each[2],
                 'a3': each[3],
                 'a4': each[4],
                 'a5': each[5]
                 } for each in questionReturn]

    return dataDict
