from datetime import datetime, timezone

import boto3
from botocore.stub import Stubber
import pytest

from app.game import Game
from app.game_service.base import BaseGameService
from app.gateway import DynamoGateway, NoSuchGame, NoSuchQuestion
from app.player import Player
from app.question import Question


class TestDynamoGateway:
    @pytest.fixture
    def example_game(self):
        game = Game(
            game_id="1",
            keywords=set(["history", "Napoleon"]),
            questions_limit=15,
            creation_time=datetime.fromtimestamp(1687468904, tz=timezone.utc),
        )

        return game

    @pytest.fixture
    def example_gameservice(self):
        class DummyGameService(BaseGameService):
            def generate_question(self, game: Game) -> Question:
                return Question.create("", ["", ""], "", 1)

        return DummyGameService()

    def test_list_player_games(self):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "1"},
                        "Keywords": {"SS": [
                            "history",
                            "Napoleon",
                        ]},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "2"},
                        "Keywords": {"SS": [
                            "mathematics",
                        ]},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "3"},
                        "Keywords": {"SS": [
                            "movies",
                        ]},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                ],
            },
            expected_params={
                "TableName": "DummyGameTable",
                "IndexName": "creation-time-index",
                "Select": "ALL_PROJECTED_ATTRIBUTES",
                "KeyConditionExpression": "PlayerId = :player_id",
                "ExpressionAttributeValues": {
                    ":player_id": {"S": "player1"},
                },
                "ScanIndexForward": False,
            },
        )

        stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "GameId": {"S": "1"},
                        "QuestionId": {"N": "1"},
                        "Prompt": {"S": "What is this?"},
                        "Options": {
                            "L": [
                                {"S": "this"},
                                {"S": "that"},
                            ]
                        },
                        "Solution": {"N": "1"},
                        "Clarification": {"S": "It's this"},
                    },
                    {
                        "GameId": {"S": "1"},
                        "QuestionId": {"N": "1"},
                        "Prompt": {"S": "What is that?"},
                        "Options": {
                            "L": [
                                {"S": "this"},
                                {"S": "that"},
                            ]
                        },
                        "Solution": {"N": "1"},
                        "Clarification": {"S": "It's that"},
                    },
                ],
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "ScanIndexForward": True,
                "Limit": 15,
            },
        )

        stubber.add_response(
            "query",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "2"},
                },
                "ScanIndexForward": True,
                "Limit": 15,
            },
        )

        stubber.add_response(
            "query",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "3"},
                },
                "ScanIndexForward": True,
                "Limit": 15,
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            games = list(gateway.list_player_games(player.player_id))

            assert len(games) == 3
            assert len(games[0].questions) == 2
            assert len(games[1].questions) == 0
            stubber.assert_no_pending_responses()

    def test_get_game(self):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "get_item",
            {
                "Item": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "1"},
                    "Keywords": {"SS": [
                        "history",
                        "Napoleon",
                    ]},
                    "CreationTime": {"N": "1687468904"},
                    "QuestionsLimit": {"N": "15"},
                },
            },
            expected_params={
                "TableName": "DummyGameTable",
                "Key": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "1"},
                },
            },
        )

        stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "GameId": {"S": "1"},
                        "QuestionId": {"N": "1"},
                        "Prompt": {"S": "What is this?"},
                        "Options": {
                            "L": [
                                {"S": "this"},
                                {"S": "that"},
                            ]
                        },
                        "Solution": {"N": "1"},
                        "Clarification": {"S": "It's this"},
                    },
                    {
                        "GameId": {"S": "1"},
                        "QuestionId": {"N": "1"},
                        "Prompt": {"S": "What is that?"},
                        "Options": {
                            "L": [
                                {"S": "this"},
                                {"S": "that"},
                            ]
                        },
                        "Solution": {"N": "1"},
                        "Clarification": {"S": "It's that"},
                    },
                ],
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "Limit": 15,
                "ScanIndexForward": True,
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            game = gateway.get_game(player.player_id, "1")

            assert len(game.questions) == 2
            stubber.assert_no_pending_responses()

    def test_get_game_nonexistent(self):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "get_item",
            {},
            expected_params={
                "TableName": "DummyGameTable",
                "Key": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "1"},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            with pytest.raises(NoSuchGame):
                gateway.get_game(player.player_id, "1")

            stubber.assert_no_pending_responses()

    def test_store_game(self, example_game):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": "DummyGameTable",
                "Item": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "1"},
                    "Keywords": {"SS": [
                        "history",
                        "Napoleon",
                    ]},
                    "CreationTime": {"N": "1687468904"},
                    "QuestionsLimit": {"N": "15"},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.store_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_store_game_with_questions(self, example_game, example_gameservice):
        example_question = example_game.quiz(example_gameservice)
        example_question.answer(1)
        example_question = example_game.quiz(example_gameservice)

        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": "DummyGameTable",
                "Item": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "1"},
                    "Keywords": {"SS": [
                        "history",
                        "Napoleon",
                    ]},
                    "CreationTime": {"N": "1687468904"},
                    "QuestionsLimit": {"N": "15"},
                },
            },
        )

        stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Item": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "1"},
                    "Prompt": {"S": ""},
                    "Options": {
                        "L": [
                            {"S": ""},
                            {"S": ""},
                        ]
                    },
                    "Solution": {"N": "1"},
                    "Choice": {"N": "1"},
                    "Clarification": {"S": ""},
                },
            },
        )

        stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Item": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "2"},
                    "Prompt": {"S": ""},
                    "Options": {
                        "L": [
                            {"S": ""},
                            {"S": ""},
                        ]
                    },
                    "Solution": {"N": "1"},
                    "Clarification": {"S": ""},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.store_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_update_game_no_questions(self, example_game):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "query",
            {
                "Count": 0,
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "Select": "COUNT",
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.update_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_update_game_current_unanswered(self, example_game, example_gameservice):
        example_game.quiz(example_gameservice)

        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "query",
            {
                "Count": 1,
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "Select": "COUNT",
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.update_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_update_game_current_answered(self, example_game, example_gameservice):
        example_question = example_game.quiz(example_gameservice)
        example_question.answer(1)

        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "query",
            {
                "Count": 1,
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "Select": "COUNT",
            },
        )

        stubber.add_response(
            "update_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Key": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "1"},
                },
                "UpdateExpression": "SET Choice = :choice",
                "ExpressionAttributeValues": {
                    ":choice": {"N": "1"},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.update_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_update_game_new_questions(self, example_game, example_gameservice):
        example_question = example_game.quiz(example_gameservice)
        example_question.answer(1)
        example_game.quiz(example_gameservice)

        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "query",
            {
                "Count": 1,
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "1"},
                },
                "Select": "COUNT",
            },
        )

        stubber.add_response(
            "update_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Key": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "1"},
                },
                "UpdateExpression": "SET Choice = :choice",
                "ExpressionAttributeValues": {
                    ":choice": {"N": "1"},
                },
            },
        )

        stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Item": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "2"},
                    "Prompt": {"S": ""},
                    "Options": {
                        "L": [
                            {"S": ""},
                            {"S": ""},
                        ]
                    },
                    "Solution": {"N": "1"},
                    "Clarification": {"S": ""},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            player = Player("player1")
            gateway.update_game(player.player_id, example_game)

            stubber.assert_no_pending_responses()

    def test_get_game_question(self):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "get_item",
            {
                "Item": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "2"},
                    "Prompt": {"S": ""},
                    "Options": {
                        "L": [
                            {"S": ""},
                            {"S": ""},
                        ]
                    },
                    "Solution": {"N": "1"},
                    "Clarification": {"S": ""},
                },
            },
            expected_params={
                "TableName": "DummyQuestionTable",
                "Key": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "2"},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            question = gateway.get_game_question("1", 2)
            assert question.solution == 1

            stubber.assert_no_pending_responses()

    def test_get_game_question_nonexistent(self):
        client = boto3.client("dynamodb")
        stubber = Stubber(client)

        stubber.add_response(
            "get_item",
            {},
            expected_params={
                "TableName": "DummyQuestionTable",
                "Key": {
                    "GameId": {"S": "1"},
                    "QuestionId": {"N": "2"},
                },
            },
        )

        with stubber:
            gateway = DynamoGateway(client)

            with pytest.raises(NoSuchQuestion):
                gateway.get_game_question("1", 2)

            stubber.assert_no_pending_responses()
