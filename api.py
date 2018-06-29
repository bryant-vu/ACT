from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Query
import json, logging

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
    input_list = list(input_data)
    for x in input_data:
        questionReturn = session.query(Questions.id,
                                           Questions.date,
                                           Questions.ans).filter(Questions.topic == x)
        dataDict = [{'id': each[0],
                        'date': each[1],
                        'ans': each[2]
                        } for each in questionReturn]

    logging.warning('{}, {}'.format(input_list,x))

    return dataDict
