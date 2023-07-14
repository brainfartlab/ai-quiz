from typing import List

from pydantic import BaseModel, Field


class QuestionModel(BaseModel):
    question: str = Field(
        description="QUESTION: the question")
    answer: str = Field(
        description="ANSWER: the correct answer to the question")
    wrong_answers: List[str] = Field(
        description="WRONG ANSWERS: three incorrect answers")
    clarification: str = Field(
        description="CLARIFICATION: a clarifying answer")


class QuestionsModel(BaseModel):
    questions: List[QuestionModel]
