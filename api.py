from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Query

engine = create_engine('sqlite:///data/question.sqlite', convert_unicode=True, echo=False)
Base = declarative_base()
Base.metadata.reflect(engine)


class Questions(Base):
    __table__ = Base.metadata.tables['circle']


session = scoped_session(sessionmaker(bind=engine))


def questions():

    questionReturn = session.query(Questions.statement, Questions.choice_a, Questions.choice_b, Questions.choice_c, Questions.choice_d)
    questionList = [each for each in questionReturn]

    return questionList


# Need to take response and return json from each question that can be rendered int he dom.
