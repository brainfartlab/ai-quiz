from dataclasses import dataclass
from datetime import datetime
import enum
import secrets
from typing import List, Set


class GameStatus(enum.Enum):
    PENDING = "PENDING"
    READY = "READY"
    FINISHED = "FINISHED"


@dataclass
class Game:
    game_id: str
    game_status: GameStatus
    keywords: Set[str]
    questions_limit: int
    creation_time: datetime

    def to_dict(self):
        return {
            "id": self.game_id,
            "keywords": list(self.keywords),
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
            game_status=GameStatus.PENDING,
            keywords=keywords,
            questions_limit=questions_limit,
            creation_time=datetime.utcnow(),
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
