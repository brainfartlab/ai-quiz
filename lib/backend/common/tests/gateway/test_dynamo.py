from datetime import datetime, timezone
import json

import boto3
from botocore.stub import ANY, Stubber
import pytest

from common.game import Game, GameStatus
from common.gateway import AmazonGateway, NoSuchGame, NoSuchQuestion
from common.player import Player
from common.question import Question


PARAM_GAME_QUEUE = "DummyGameQueue"
PARAM_GAME_TABLE = "DummyGameTable"
PARAM_QUESTION_TABLE = "DummyQuestionTable"
PARAM_TOKEN_TABLE = "DummyTokenTable"


class TestAmazonGateway:
    @pytest.fixture
    def example_player(self):
        player = Player(
            player_id="player1",
        )

        return player

    @pytest.fixture
    def example_game(self):
        game = Game(
            game_id="game1",
            game_status=GameStatus.READY,
            keywords=set(["history", "Napoleon"]),
            questions_limit=15,
            creation_time=datetime.fromtimestamp(1687468904, tz=timezone.utc),
        )

        return game

    @pytest.fixture
    def example_question(self):
        question = Question(
            index=1,
            prompt="What is love?",
            correct_answer="Baby, don't hurt me",
            wrong_answers=[
                "Baby, don't yoghurt me",
                "Chemicals",
            ],
            clarification="Love was first discovered in 1939 in an LSD experiment",
        )

        return question

    def test_list_player_games(self, example_player):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "game1"},
                        "Keywords": {
                            "SS": [
                                "history",
                                "Napoleon",
                            ]
                        },
                        "GameStatus": {"S": "READY"},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "2"},
                        "Keywords": {
                            "SS": [
                                "mathematics",
                            ]
                        },
                        "GameStatus": {"S": "PENDING"},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                    {
                        "PlayerId": {"S": "player1"},
                        "GameId": {"S": "3"},
                        "Keywords": {
                            "SS": [
                                "movies",
                            ]
                        },
                        "GameStatus": {"S": "FINISHED"},
                        "CreationTime": {"N": "1687468904"},
                        "QuestionsLimit": {"N": "15"},
                    },
                ],
            },
            expected_params={
                "TableName": PARAM_GAME_TABLE,
                "IndexName": "creation-time-index",
                "Select": "ALL_PROJECTED_ATTRIBUTES",
                "KeyConditionExpression": "PlayerId = :player_id",
                "ExpressionAttributeValues": {
                    ":player_id": {"S": "player1"},
                },
                "ScanIndexForward": False,
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            games = list(gateway.list_player_games(example_player))

            assert len(games) == 3
            assert games[0].game_status == GameStatus.READY
            assert games[1].game_status == GameStatus.PENDING
            assert games[2].game_status == GameStatus.FINISHED
            dynamo_stubber.assert_no_pending_responses()

    def test_get_game(self, example_player):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "get_item",
            {
                "Item": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "game1"},
                    "GameStatus": {"S": "PENDING"},
                    "Keywords": {
                        "SS": [
                            "history",
                            "Napoleon",
                        ]
                    },
                    "CreationTime": {"N": "1687468904"},
                    "QuestionsLimit": {"N": "15"},
                },
            },
            expected_params={
                "TableName": PARAM_GAME_TABLE,
                "Key": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "game1"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            game = gateway.get_game(example_player, "game1")

            assert game.game_id == "game1"
            assert game.game_status == GameStatus.PENDING
            dynamo_stubber.assert_no_pending_responses()

    def test_get_game_nonexistent(self, example_player):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "get_item",
            {},
            expected_params={
                "TableName": PARAM_GAME_TABLE,
                "Key": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "game1"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            with pytest.raises(NoSuchGame):
                gateway.get_game(example_player, "game1")

            dynamo_stubber.assert_no_pending_responses()

    def test_store_game(self, example_game, example_player):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": PARAM_GAME_TABLE,
                "Item": {
                    "PlayerId": {"S": "player1"},
                    "GameId": {"S": "game1"},
                    "GameStatus": {"S": "READY"},
                    "Keywords": ANY,
                    "CreationTime": {"N": "1687468904"},
                    "QuestionsLimit": {"N": "15"},
                },
            },
        )

        sqs_client = boto3.client("sqs")
        sqs_stubber = Stubber(sqs_client)

        sqs_stubber.add_response(
            "send_message",
            {},
            expected_params={
                "QueueUrl": PARAM_GAME_QUEUE,
                "MessageBody": json.dumps({
                    "game_id": "game1"
                }),
            },
        )

        with dynamo_stubber, sqs_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                sqs_client=sqs_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            gateway.store_game(example_player, example_game)

            dynamo_stubber.assert_no_pending_responses()

    def test_update_game_status(self, example_player, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "update_item",
            {},
            expected_params={
                "TableName": PARAM_GAME_TABLE,
                "Key": {
                    "GameId": {"S": "game1"},
                },
                "UpdateExpression": "SET GameStatus = :game_status",
                "ConditionExpression": "GameStatus != :finished",
                "ExpressionAttributeValues": {
                    ":game_status": {"S": "FINISHED"},
                    ":finished": {"S": "FINISHED"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            example_game.game_status = GameStatus.FINISHED
            gateway.update_game_status(example_player, example_game)

            dynamo_stubber.assert_no_pending_responses()

    def test_list_game_questions(self, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "GameId": {"S": "game1"},
                        "QuestionId": {"N": "1"},
                        "Prompt": {"S": ""},
                        "Answer": {"S": ""},
                        "Choice": {"S": ""},
                        "WrongAnswers": {
                            "L": [
                                {"S": ""},
                                {"S": ""},
                            ]
                        },
                        "Clarification": {"S": ""},
                    },
                    {
                        "GameId": {"S": "game1"},
                        "QuestionId": {"N": "2"},
                        "Prompt": {"S": ""},
                        "Answer": {"S": ""},
                        "WrongAnswers": {
                            "L": [
                                {"S": ""},
                                {"S": ""},
                            ]
                        },
                        "Clarification": {"S": ""},
                    },
                    {
                        "GameId": {"S": "game1"},
                        "QuestionId": {"N": "3"},
                        "Prompt": {"S": ""},
                        "Answer": {"S": ""},
                        "WrongAnswers": {
                            "L": [
                                {"S": ""},
                                {"S": ""},
                            ]
                        },
                        "Clarification": {"S": ""},
                    },
                ],
            },
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "KeyConditionExpression": "GameId = :game_id",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "game1"},
                },
                "Limit": 15,
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            questions = list(gateway.list_game_questions(example_game))

            assert len(questions) == 3
            assert questions[0].is_answered
            assert not questions[1].is_answered
            assert not questions[2].is_answered

            dynamo_stubber.assert_no_pending_responses()

    def test_list_game_unanswered_questions(self, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "query",
            {
                "Items": [
                    {
                        "GameId": {"S": "game1"},
                        "QuestionId": {"N": "2"},
                        "Prompt": {"S": ""},
                        "Answer": {"S": ""},
                        "WrongAnswers": {
                            "L": [
                                {"S": ""},
                                {"S": ""},
                            ]
                        },
                        "Clarification": {"S": ""},
                    },
                    {
                        "GameId": {"S": "game1"},
                        "QuestionId": {"N": "3"},
                        "Prompt": {"S": ""},
                        "Answer": {"S": ""},
                        "WrongAnswers": {
                            "L": [
                                {"S": ""},
                                {"S": ""},
                            ]
                        },
                        "Clarification": {"S": ""},
                    },
                ],
            },
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "KeyConditionExpression": "GameId = :game_id",
                "FilterExpression": "attribute_not_exists(Choice)",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "game1"},
                },
                "Limit": 15,
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            questions = list(gateway.list_game_unanswered_questions(example_game))

            assert len(questions) == 2
            assert not questions[0].is_answered
            assert not questions[1].is_answered

            dynamo_stubber.assert_no_pending_responses()

    def test_count_game_unanswered_questions(self, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "query",
            {
                "Count": 2,
            },
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "KeyConditionExpression": "GameId = :game_id",
                "FilterExpression": "attribute_not_exists(Choice)",
                "ExpressionAttributeValues": {
                    ":game_id": {"S": "game1"},
                },
                "Select": "Count",
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            count = gateway.count_game_unanswered_questions(example_game)

            assert count == 2

            dynamo_stubber.assert_no_pending_responses()

    def test_get_game_question(self, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "get_item",
            {
                "Item": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "2"},
                    "Prompt": {"S": ""},
                    "Answer": {"S": ""},
                    "WrongAnswers": {
                        "L": [
                            {"S": ""},
                            {"S": ""},
                        ]
                    },
                    "Clarification": {"S": ""},
                },
            },
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "Key": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "2"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            question = gateway.get_game_question(example_game, 2)
            assert question.correct_answer == ""

            dynamo_stubber.assert_no_pending_responses()

    def test_get_game_question_nonexistent(self, example_game):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "get_item",
            {},
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "Key": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "2"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            with pytest.raises(NoSuchQuestion):
                gateway.get_game_question(example_game, 2)

            dynamo_stubber.assert_no_pending_responses()

    def test_store_game_question(self, example_game, example_question):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "put_item",
            {},
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "ConditionExpression": "attribute_not_exists(GameId) "
                "and attribute_not_exists(QuestionId)",
                "Item": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "1"},
                    "Prompt": {"S": "What is love?"},
                    "Answer": {"S": "Baby, don't hurt me"},
                    "WrongAnswers": {
                        "L": [
                            {"S": "Baby, don't yoghurt me"},
                            {"S": "Chemicals"},
                        ]
                    },
                    "Clarification": {
                        "S": "Love was first discovered in 1939 in an LSD experiment"
                    },
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            gateway.store_game_question(example_game, example_question)

            dynamo_stubber.assert_no_pending_responses()

    def test_store_game_questions(self, example_game, example_question):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "batch_write_item",
            {},
            expected_params={
                "RequestItems": {
                    PARAM_GAME_TABLE: [
                        {
                            "PutRequest": {
                                "Item": {
                                    "GameId": {"S": "game1"},
                                    "QuestionId": {"N": "1"},
                                    "Prompt": {"S": "What is love?"},
                                    "Answer": {"S": "Baby, don't hurt me"},
                                    "WrongAnswers": {
                                        "L": [
                                            {"S": "Baby, don't yoghurt me"},
                                            {"S": "Chemicals"},
                                        ]
                                    },
                                    "Clarification": {
                                        "S": "Love was first discovered in 1939 in an "
                                        "LSD experiment"
                                    },
                                },
                            },
                        },
                        {
                            "PutRequest": {
                                "Item": {
                                    "GameId": {"S": "game1"},
                                    "QuestionId": {"N": "1"},
                                    "Prompt": {"S": "What is love?"},
                                    "Answer": {"S": "Baby, don't hurt me"},
                                    "WrongAnswers": {
                                        "L": [
                                            {"S": "Baby, don't yoghurt me"},
                                            {"S": "Chemicals"},
                                        ]
                                    },
                                    "Clarification": {
                                        "S": "Love was first discovered in 1939 in an "
                                        "LSD experiment"
                                    },
                                },
                            },
                        },
                    ],
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            gateway.store_game_questions(
                example_game,
                [
                    example_question,
                    example_question,
                ],
            )

            dynamo_stubber.assert_no_pending_responses()

    def test_update_game_question_choice(self, example_game, example_question):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "update_item",
            {},
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "Key": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "1"},
                },
                "ConditionExpression": "attribute_not_exists(Choice)",
                "UpdateExpression": "SET Choice = :choice",
                "ExpressionAttributeValues": {
                    ":choice": {"S": "Chemicals"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            example_question.answer("Chemicals")
            gateway.update_game_question_choice(example_game, example_question)

            dynamo_stubber.assert_no_pending_responses()

    def test_update_game_question_choice_last(self, example_game, example_question):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        dynamo_stubber.add_response(
            "update_item",
            {},
            expected_params={
                "TableName": PARAM_QUESTION_TABLE,
                "Key": {
                    "GameId": {"S": "game1"},
                    "QuestionId": {"N": "1"},
                },
                "ConditionExpression": "attribute_not_exists(Choice)",
                "UpdateExpression": "SET Choice = :choice",
                "ExpressionAttributeValues": {
                    ":choice": {"S": "Chemicals"},
                },
            },
        )

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            example_question.answer("Chemicals")
            gateway.update_game_question_choice(example_game, example_question)

            dynamo_stubber.assert_no_pending_responses()

    def test_update_game_question_choice_no_choice(
        self, example_game, example_question
    ):
        dynamo_client = boto3.client("dynamodb")
        dynamo_stubber = Stubber(dynamo_client)

        with dynamo_stubber:
            gateway = AmazonGateway(
                dynamo_client=dynamo_client,
                game_queue=PARAM_GAME_QUEUE,
                game_table=PARAM_GAME_TABLE,
                question_table=PARAM_QUESTION_TABLE,
                token_table=PARAM_TOKEN_TABLE,
            )

            gateway.update_game_question_choice(example_game, example_question)

            dynamo_stubber.assert_no_pending_responses()
