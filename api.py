from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Query
import json

engine = create_engine('sqlite:///data/question.sqlite', convert_unicode=True, echo=False)
Base = declarative_base()
Base.metadata.reflect(engine)


class Questions(Base):
    __table__ = Base.metadata.tables['circle']


session = scoped_session(sessionmaker(bind=engine))


def question_list():
    questionQuery = session.query(Questions.test_date)

    questionList = [each for (each,) in questionQuery]

    return questionList


def questions(input_data):

    questionReturn = session.query(Questions.statement,
                                   Questions.choice_a,
                                   Questions.choice_b,
                                   Questions.choice_c,
                                   Questions.choice_d).filter(Questions.test_date == input_data)

    dataDict = [{'Question': each[0],
                 'Answer_1': each[1],
                 'Answer_2': each[2],
                 'Answer_3': each[3],
                 'Answer_5': each[4]
                 } for each in questionReturn]

    return dataDict
