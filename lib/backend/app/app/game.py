from dataclasses import dataclass, field
from datetime import datetime
import secrets
from typing import List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .game_service.base import GameService

from .question import Question


@dataclass
class Game:
    game_id: str
    keywords: Set[str]
    questions_limit: int

    creation_time: datetime = field(default_factory=datetime.utcnow)
    questions: List[Question] = field(default_factory=list)

    @property
    def is_latest_answered(self):
        return self.questions[-1].is_answered

    def quiz(self, service: "GameService") -> Question:
        if len(self.questions) == 0 or self.is_latest_answered:
            if len(self.questions) == self.questions_limit:
                raise QuestionsLimitReached(self)

            question = service.generate_question(self)
            self.questions.append(question)

            return question
        else:
            return self.questions[-1]

    @property
    def questions_answered(self):
        if not self.questions or self.questions[-1].is_answered:
            return len(self.questions)
        else:
            return len(self.questions) - 1

    def to_dict(self):
        return {
            "id": self.game_id,
            "keywords": list(self.keywords),
            "questions_count": self.questions_answered,
            "questions_limit": self.questions_limit,
            "creation_time": int(1000 * self.creation_time.timestamp()),
        }

    @staticmethod
    def create(keywords: List[str], questions_limit: int):
        errors = []

        if len(keywords) == 0:
            errors.append(FieldError("keywords", "No keywords provided"))

        if questions_limit < 1:
            errors.append(FieldError("questions_limit", "Must be larger than 0"))

        if errors:
            raise InvalidGame(errors)

        game = Game(
            game_id=secrets.token_hex(),
            keywords=keywords,
            questions_limit=questions_limit,
        )

        return game


class QuestionsLimitReached(Exception):
    def __init__(self, game: Game):
        self.game = game


@dataclass
class FieldError:
    field: str
    message: str


class InvalidGame(Exception):
    def __init__(self, errors: List[FieldError]):
        self.errors = errors

    def to_json(self):
        return {
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                }
                for e in self.errors
            ]
        }
