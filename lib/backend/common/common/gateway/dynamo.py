from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Iterator, List

import boto3
from boto3.dynamodb.types import (
    TypeDeserializer,
    TypeSerializer,
)

from .base import BaseGateway, NoSuchGame, NoSuchQuestion, UnknownToken
from ..game import Game, GameStatus
from ..player import Player
from ..question import Question


def deserialize(record: Dict[str, Any]) -> Dict[str, Any]:
    deserializer = TypeDeserializer()
    return dict((k, deserializer.deserialize(v)) for k, v in record.items())


def serialize(record: Dict[str, Any]) -> Dict[str, Any]:
    serializer = TypeSerializer()
    return dict((k, serializer.serialize(v)) for k, v in record.items())


def hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


@dataclass
class DynamoGateway(BaseGateway):
    game_table: str
    question_table: str
    token_table: str

    client: boto3.Session = field(
        repr=False, default_factory=lambda: boto3.client("dynamodb")
    )

    def list_player_games(
        self,
        player: Player,
    ) -> Iterator[Game]:
        paginator = self.client.get_paginator("query")

        for page in paginator.paginate(
            TableName=self.game_table,
            IndexName="creation-time-index",
            Select="ALL_PROJECTED_ATTRIBUTES",
            KeyConditionExpression="PlayerId = :player_id",
            ExpressionAttributeValues={
                ":player_id": {"S": player.player_id},
            },
            ScanIndexForward=False,
        ):
            for item in page.get("Items", []):
                game_data = deserialize(item)

                yield Game(
                    game_id=game_data["GameId"],
                    game_status=GameStatus(game_data["GameStatus"]),
                    keywords=set(game_data["Keywords"]),
                    questions_limit=int(game_data["QuestionsLimit"]),
                    creation_time=datetime.fromtimestamp(
                        int(game_data["CreationTime"]),
                        tz=timezone.utc,
                    ),
                )

    def store_game(self, player: Player, game: Game):
        response = self.client.put_item(
            TableName=self.game_table,
            Item=serialize(
                {
                    "PlayerId": player.player_id,
                    "GameId": game.game_id,
                    "GameStatus": game.game_status.value,
                    "Keywords": game.keywords,
                    "QuestionsLimit": game.questions_limit,
                    "CreationTime": int(game.creation_time.timestamp()),
                }
            ),
        )

        # TODO: handle response
        print(response)

    def update_game_status(self, player: Player, game: Game):
        response = self.client.update_item(
            TableName=self.game_table,
            Key={
                "GameId": {"S": game.game_id},
            },
            ConditionExpression="GameStatus != :finished",
            UpdateExpression="SET GameStatus = :game_status",
            ExpressionAttributeValues={
                ":game_status": {"S": game.game_status.value},
                ":finished": {"S": GameStatus.FINISHED.value},
            },
        )

        # TODO: use response
        print(response)

    def get_game(
        self,
        player: Player,
        game_id: str,
    ) -> Game:
        response = self.client.get_item(
            TableName=self.game_table,
            Key=serialize(
                {
                    "PlayerId": player.player_id,
                    "GameId": game_id,
                }
            ),
        )

        if "Item" in response:
            game_data = deserialize(response["Item"])

            return Game(
                game_id=game_data["GameId"],
                game_status=GameStatus(game_data["GameStatus"]),
                keywords=game_data["Keywords"],
                questions_limit=int(game_data["QuestionsLimit"]),
                creation_time=datetime.fromtimestamp(
                    int(game_data["CreationTime"]),
                    tz=timezone.utc,
                ),
            )
        else:
            raise NoSuchGame(game_id)

    def list_game_questions(
        self,
        game: Game,
    ) -> List[Question]:
        paginator = self.client.get_paginator("query")

        for page in paginator.paginate(
            TableName=self.question_table,
            KeyConditionExpression="GameId = :game_id",
            ExpressionAttributeValues={
                ":game_id": {"S": game.game_id},
            },
            Limit=game.questions_limit,
        ):
            for item in page.get("Items", []):
                question_data = deserialize(item)

                choice = question_data.get("Choice")

                yield Question(
                    index=int(question_data["QuestionId"]),
                    prompt=question_data["Prompt"],
                    correct_answer=question_data["Answer"],
                    wrong_answers=question_data["WrongAnswers"],
                    choice=choice,
                    clarification=question_data["Clarification"],
                )

    def count_game_unanswered_questions(
        self,
        game: Game,
    ) -> List[Question]:
        paginator = self.client.get_paginator("query")
        count = 0

        for page in paginator.paginate(
            TableName=self.question_table,
            KeyConditionExpression="GameId = :game_id",
            FilterExpression="attribute_not_exists(Choice)",
            ExpressionAttributeValues={
                ":game_id": {"S": game.game_id},
            },
            Select="Count",
        ):
            count += page["Count"]

        return count

    def list_game_unanswered_questions(
        self,
        game: Game,
        limit: int = None,
    ) -> Question:
        paginator = self.client.get_paginator("query")

        for page in paginator.paginate(
            TableName=self.question_table,
            KeyConditionExpression="GameId = :game_id",
            FilterExpression="attribute_not_exists(Choice)",
            ExpressionAttributeValues={
                ":game_id": {"S": game.game_id},
            },
            Limit=game.questions_limit,
        ):
            for item in page.get("Items", []):
                question_data = deserialize(item)

                choice = question_data.get("Choice")

                yield Question(
                    index=int(question_data["QuestionId"]),
                    prompt=question_data["Prompt"],
                    correct_answer=question_data["Answer"],
                    wrong_answers=question_data["WrongAnswers"],
                    choice=choice,
                    clarification=question_data["Clarification"],
                )

    def get_game_question(
        self,
        game: Game,
        question_index: int,
    ) -> Question:
        response = self.client.get_item(
            TableName=self.question_table,
            Key=serialize(
                {
                    "GameId": game.game_id,
                    "QuestionId": question_index,
                }
            ),
        )

        if "Item" in response:
            question_data = deserialize(response["Item"])

            choice = question_data.get("Choice")

            return Question(
                index=int(question_data["QuestionId"]),
                prompt=question_data["Prompt"],
                correct_answer=question_data["Answer"],
                wrong_answers=question_data["WrongAnswers"],
                choice=choice,
                clarification=question_data["Clarification"],
            )
        else:
            raise NoSuchQuestion(game.game_id, question_index)

    def _translate_question(self, game: Game, question: Question) -> Dict[str, Any]:
        question_data = {
            "GameId": game.game_id,
            "QuestionId": question.index,
            "Prompt": question.prompt,
            "Answer": question.correct_answer,
            "WrongAnswers": question.wrong_answers,
            "Clarification": question.clarification,
        }

        if question.is_answered:
            question_data["Choice"] = question.choice

        return question_data

    def store_game_question(
        self,
        game: Game,
        question: Question,
    ):
        response = self.client.put_item(
            TableName=self.question_table,
            ConditionExpression="attribute_not_exists(GameId) "
            "and attribute_not_exists(QuestionId)",
            Item=serialize(self._translate_question(game, question)),
        )

        # TODO: handle response
        print(response)

    def store_game_questions(
        self,
        game: Game,
        questions: List[Question],
    ):
        response = self.client.batch_write_item(
            RequestItems={
                self.game_table: [
                    {
                        "PutRequest": {
                            "Item": serialize(self._translate_question(game, question)),
                        },
                    }
                    for question in questions
                ],
            },
        )

        # TODO: handle response
        print(response)

    def update_game_question_choice(
        self,
        game: Game,
        question: Question,
    ):
        if question.is_answered:
            self.client.update_item(
                TableName=self.question_table,
                Key=serialize(
                    {
                        "GameId": game.game_id,
                        "QuestionId": question.index,
                    }
                ),
                ConditionExpression="attribute_not_exists(Choice)",
                UpdateExpression="SET Choice = :choice",
                ExpressionAttributeValues=serialize(
                    {
                        ":choice": question.choice,
                    }
                ),
            )

    def get_player_by_token(self, token: str) -> Player:
        token_hash = hash(token)

        response = self.client.get_item(
            TableName=self.token_table,
            Key=serialize(
                {
                    "TokenHash": token_hash,
                }
            ),
        )

        if "Item" in response:
            user_data = deserialize(response["Item"])

            return Player(user_data["PlayerId"])
        else:
            raise UnknownToken(token)

    def store_player_by_token(self, token: str, player: Player, duration: int = 3600):
        token_hash = hash(token)

        epoch = int(datetime.now().timestamp())
        epoch += duration

        user_data = {
            "TokenHash": token_hash,
            "PlayerId": player.player_id,
            "ExpirationEpoch": epoch,
        }

        response = self.client.put_item(
            TableName=self.token_table,
            Item=serialize(user_data),
        )

        print(response)
