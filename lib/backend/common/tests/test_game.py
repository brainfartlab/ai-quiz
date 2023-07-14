from common.game import Game, GameStatus


class TestGame:
    def test_create(self):
        game = Game.create(
            keywords=["history", "Napoleon"],
            questions_limit=15,
        )

        assert game.game_status == GameStatus.PENDING
        assert game.keywords == ["history", "Napoleon"]
        assert game.questions_limit == 15
