from dataclasses import dataclass

import pytest

from app.game import Game, QuestionsLimitReached
from app.game_service.base import BaseGameService
from app.gateway.base import BaseGateway
from app.question import Question


class TestGame:
    @pytest.fixture
    def example_gameservice(self):
        class DummyGameService(BaseGameService):
            def generate_question(self, game: Game) -> Question:
                return Question.create("", ["", ""], "", 1)

        return DummyGameService()

    @pytest.fixture
    def example_gateway(self):
        @dataclass
        class DummyGateway(BaseGateway):
            def get_game_question(self, game: Game, question_id: int) -> Question:
                return Question.create(question_id, "", ["", ""], "", 1)

        return DummyGateway()

    def test_create(self):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=15,
        )

        assert game.keywords == ["history", "Napoleon"]
        assert len(game.questions) == 0
        assert game.questions_limit == 15

    def test_quiz_empty(
        self,
        example_gameservice,
    ):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=2,
        )
        question = game.quiz(example_gameservice)

        assert len(game.questions) == 1
        assert not question.is_answered

    def test_quiz_last_is_answered(
        self,
        example_gameservice,
    ):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=2,
        )
        question1 = game.quiz(example_gameservice)
        question1.answer(1)
        question2 = game.quiz(example_gameservice)

        assert len(game.questions) == 2
        assert question1.is_answered
        assert not question2.is_answered

    def test_quiz_last_is_unanswered(
        self,
        example_gameservice,
    ):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=2,
        )
        question1 = game.quiz(example_gameservice)
        question2 = game.quiz(example_gameservice)

        assert len(game.questions) == 1
        assert not question1.is_answered
        assert question1 == question2

    def test_quiz_full(
        self,
        example_gameservice,
    ):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=2,
        )
        question1 = game.quiz(example_gameservice)
        question1.answer(1)
        question2 = game.quiz(example_gameservice)
        question2.answer(1)

        with pytest.raises(QuestionsLimitReached):
            game.quiz(example_gameservice)

        assert len(game.questions) == 2
