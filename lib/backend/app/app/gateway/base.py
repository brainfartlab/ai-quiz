from abc import ABC, abstractmethod
from typing import List

from ..game import Game
from ..question import Question


class NoSuchGame(Exception):
    def __init__(self, game_id: str):
        self.game_id = game_id


class NoSuchQuestion(Exception):
    def __init__(self, game_id: str, question_index: int):
        self.game_id = game_id
        self.question_index = question_index


class UnknownToken(Exception):
    def __init__(self, token: str):
        self.token = token


class BaseGateway(ABC):
    @abstractmethod
    def list_player_games(
        self,
        player_id: str,
    ) -> List[Game]:
        raise NotImplementedError

    @abstractmethod
    def store_game(self, player_id: str, game: Game):
        raise NotImplementedError

    @abstractmethod
    def update_game(self, player_id: str, game: Game):
        raise NotImplementedError

    @abstractmethod
    def get_game(
        self,
        player_id: str,
        game_id: str,
    ) -> Game:
        raise NotImplementedError

    @abstractmethod
    def list_game_questions(
        self,
        game_id: str,
        limit: int,
    ) -> List[Question]:
        raise NotImplementedError

    @abstractmethod
    def count_game_questions(
        self,
        game_id: str,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_game_question(
        self,
        game_id: str,
        question_id: int,
    ) -> Question:
        raise NotImplementedError

    @abstractmethod
    def store_game_question(
        self,
        game_id: str,
        question_id: int,
        question: Question,
    ):
        raise NotImplementedError

    @abstractmethod
    def update_game_question(
        self,
        game_id: str,
        question_id: int,
        question: Question,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_player_by_token(
        self,
        token: str,
    ) -> Player:
        raise NotImplementedError

    @abstractmethod
    def store_player_by_token(
        self,
        token: str,
        player: Player,
    ):
        raise NotImplementedError
