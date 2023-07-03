from dataclasses import dataclass
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
    solution: int
    clarification: str


@dataclass
class Question:
    prompt: str
    options: List[int]
    clarification: str
    solution: int
    choice: int = None

    def pose(self) -> Dict[str, Any]:
        return {
            "question": self.prompt,
            "options": self.options,
        }

    def describe(self) -> Dict[str, Any]:
        return {
            "question": self.prompt,
            "is_answered": self.is_answered,
        }

    @property
    def is_answered(self) -> bool:
        return self.choice is not None

    @property
    def answered_correctly(self) -> bool:
        if self.choice is None:
            raise NoAnswerProvided

        return self.choice == self.solution

    @property
    def solution_str(self) -> str:
        return self.options[self.solution - 1]

    def answer(self, choice: int) -> QuestionFeedback:
        if choice < 1 or choice > len(self.options):
            raise InvalidAnswer

        self.choice = choice

        return QuestionFeedback(
            result=self.answered_correctly,
            solution=self.solution,
            clarification=self.clarification,
        )

    @staticmethod
    def create(prompt: str, options: List[int], clarification: str, solution: int):
        if solution < 1 or solution > len(options):
            raise InvalidQuestion

        question = Question(
            prompt=prompt,
            options=options,
            clarification=clarification,
            solution=solution,
        )

        return question
