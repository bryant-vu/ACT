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

def question_date():
    questionQuery = session.query(Questions.date)

    questionListDate = [each for (each,) in questionQuery]

    return questionListDate

def question_list():
    questionQuery = session.query(Questions.topic)

    questionListTopic = [each for (each,) in questionQuery]

    return questionListTopic


def questions(input_data):
    input_data = input_data.split(",")
    input_data = [x.strip(" ") for x in input_data]
    if len(input_data) == 1:
            questionReturn = session.query(Questions.id,
                                           Questions.date,
                                           Questions.ans).filter(Questions.topic == input_data[0])
            dataDict = [{'id': each[0],
                            'date': each[1],
                            'ans': each[2]
                            } for each in questionReturn]

    else:
        questionReturn = session.query(Questions.id,
                                       Questions.date,
                                       Questions.ans).filter(Questions.topic.in_(input_data))
        dataDict = [{'id': each[0],
                        'date': each[1],
                        'ans': each[2]
                        } for each in questionReturn]

    logging.warning('{}'.format(input_data))

    return dataDict
