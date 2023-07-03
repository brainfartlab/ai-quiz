from abc import ABC, abstractmethod

from ..game import Game
from ..question import Question


class BaseGameService(ABC):
    @abstractmethod
    def generate_question(self, game: Game) -> Question:
        raise NotImplementedError
