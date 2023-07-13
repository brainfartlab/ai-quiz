from dataclasses import dataclass
import random
from typing import Any, Dict, List


class InvalidQuestion(Exception):
    pass


class InvalidAnswer(Exception):
    pass


class NoAnswerProvided(Exception):
    pass


@dataclass
class QuestionFeedback:
    result: bool
    correct_answer: str
    clarification: str


@dataclass
class Question:
    correct_answer: str
    clarification: str
    index: int
    prompt: str
    wrong_answers: List[str]

    choice: str = None

    def pose(self) -> Dict[str, Any]:
        options = [self.correct_answer, *self.wrong_answers]
        random.shuffle(options)

        return {
            "prompt": self.prompt,
            "options": options,
        }

    def describe(self) -> Dict[str, Any]:
        return {
            "question": self.prompt,
            "is_answered": self.is_answered,
        }

    @property
    def is_answered(self) -> bool:
        return self.choice is not None

    def answer(self, choice: str) -> QuestionFeedback:
        if choice == self.answer or choice in self.wrong_answers:
            self.choice = choice

            return QuestionFeedback(
                result=self.choice == self.correct_answer,
                correct_answer=self.answer,
                clarification=self.clarification,
            )

        raise InvalidAnswer

    @staticmethod
    def create(
        index: int,
        prompt: str,
        correct_answer: str,
        wrong_answers: List[str],
        clarification: str,
    ):
        if correct_answer in wrong_answers:
            raise InvalidQuestion

        question = Question(
            correct_answer=correct_answer,
            clarification=clarification,
            index=index,
            prompt=prompt,
            wrong_answers=wrong_answers,
        )

        return question
