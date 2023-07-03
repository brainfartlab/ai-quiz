from dataclasses import dataclass
from datetime import datetime, timezone
import itertools
from typing import Any, Dict, Iterator, List

import boto3
from boto3.dynamodb.types import (
    TypeDeserializer,
    TypeSerializer,
)

from .base import BaseGateway, NoSuchGame, NoSuchQuestion
from ..game import Game
from ..question import Question


def deserialize(record: Dict[str, Any]) -> Dict[str, Any]:
    deserializer = TypeDeserializer()
    return dict((k, deserializer.deserialize(v)) for k, v in record.items())


def serialize(record: Dict[str, Any]) -> Dict[str, Any]:
    serializer = TypeSerializer()
    return dict((k, serializer.serialize(v)) for k, v in record.items())


@dataclass
class DynamoGateway(BaseGateway):
    game_table: str
    question_table: str

    def __post_init__(self, client=boto3.client("dynamodb")):
        self._client = client

    def list_player_games(
        self,
        player_id: str,
    ) -> Iterator[Game]:
        paginator = self._client.get_paginator("query")

        for page in paginator.paginate(
            TableName=self.game_table,
            IndexName="creation-time-index",
            Select="ALL_PROJECTED_ATTRIBUTES",
            KeyConditionExpression="PlayerId = :player_id",
            ExpressionAttributeValues={
                ":player_id": {"S": player_id},
            },
            ScanIndexForward=False,
        ):
            for item in page.get("Items", []):
                game_data = deserialize(item)
                game_questions = list(
                    self.list_game_questions(
                        game_data["GameId"], int(game_data["QuestionsLimit"])
                    )
                )

                yield Game(
                    game_id=game_data["GameId"],
                    keywords=set(game_data["Keywords"]),
                    questions_limit=int(game_data["QuestionsLimit"]),
                    questions=game_questions,
                    creation_time=datetime.fromtimestamp(
                        int(game_data["CreationTime"]),
                        tz=timezone.utc,
                    ),
                )

    def store_game(self, player_id: str, game: Game):
        response = self._client.put_item(
            TableName=self.game_table,
            Item=serialize(
                {
                    "PlayerId": player_id,
                    "GameId": game.game_id,
                    "Keywords": game.keywords,
                    "QuestionsLimit": game.questions_limit,
                    "CreationTime": int(game.creation_time.timestamp()),
                }
            ),
        )

        # TODO: handle response
        print(response)

        for index, question in enumerate(game.questions):
            self.store_game_question(game.game_id, index + 1, question)

    def update_game(self, player_id: str, game: Game):
        checkpoint = self.count_game_questions(game.game_id)

        if checkpoint > 0:
            # update the current question
            self.update_game_question(
                game.game_id, checkpoint, game.questions[checkpoint - 1]
            )

        # store the new questions
        for index, question in itertools.dropwhile(
            lambda x: x[0] + 1 <= checkpoint, enumerate(game.questions)
        ):
            self.store_game_question(game.game_id, index + 1, question)

        # TODO: handle response

    def get_game(
        self,
        player_id: str,
        game_id: str,
    ) -> Game:
        response = self._client.get_item(
            TableName=self.game_table,
            Key=serialize(
                {
                    "PlayerId": player_id,
                    "GameId": game_id,
                }
            ),
        )

        if "Item" in response:
            game_data = deserialize(response["Item"])
            game_questions = list(
                self.list_game_questions(
                    game_data["GameId"], int(game_data["QuestionsLimit"])
                )
            )

            return Game(
                game_id=game_data["GameId"],
                keywords=game_data["Keywords"],
                questions=game_questions,
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
        game_id: str,
        limit: int,
    ) -> List[Question]:
        paginator = self._client.get_paginator("query")

        for page in paginator.paginate(
            TableName=self.question_table,
            KeyConditionExpression="GameId = :game_id",
            ExpressionAttributeValues={
                ":game_id": {"S": game_id},
            },
            ScanIndexForward=True,
            Limit=limit,
        ):
            for item in page.get("Items", []):
                question_data = deserialize(item)

                choice = question_data.get("Choice")

                yield Question(
                    prompt=question_data["Prompt"],
                    options=question_data["Options"],
                    solution=int(question_data["Solution"]),
                    choice=int(choice) if choice else choice,
                    clarification=question_data["Clarification"],
                )

    def count_game_questions(
        self,
        game_id: str,
    ) -> int:
        paginator = self._client.get_paginator("query")
        count = 0

        for page in paginator.paginate(
            TableName=self.question_table,
            KeyConditionExpression="GameId = :game_id",
            ExpressionAttributeValues={
                ":game_id": {"S": game_id},
            },
            Select="COUNT",
        ):
            count += page["Count"]

        return count

    def get_game_question(
        self,
        game_id: str,
        question_id: int,
    ) -> Question:
        response = self._client.get_item(
            TableName=self.question_table,
            Key=serialize(
                {
                    "GameId": game_id,
                    "QuestionId": question_id,
                }
            ),
        )

        if "Item" in response:
            question_data = deserialize(response["Item"])

            choice = question_data.get("Choice")

            return Question(
                prompt=question_data["Prompt"],
                options=question_data["Options"],
                solution=int(question_data["Solution"]),
                choice=int(choice) if choice else choice,
                clarification=question_data["Clarification"],
            )
        else:
            raise NoSuchQuestion(game_id, question_id)

    def store_game_question(
        self,
        game_id: str,
        question_id: int,
        question: Question,
    ):
        question_data = {
            "GameId": game_id,
            "QuestionId": question_id,
            "Prompt": question.prompt,
            "Options": question.options,
            "Solution": question.solution,
            "Clarification": question.clarification,
        }

        if question.is_answered:
            question_data["Choice"] = question.choice

        response = self._client.put_item(
            TableName=self.question_table,
            Item=serialize(question_data),
        )

        # TODO: handle response
        print(response)

    def update_game_question(
        self,
        game_id: str,
        question_id: int,
        question: Question,
    ):
        if question.is_answered:
            self._client.update_item(
                TableName=self.question_table,
                Key=serialize(
                    {
                        "GameId": game_id,
                        "QuestionId": question_id,
                    }
                ),
                UpdateExpression="SET Choice = :choice",
                ExpressionAttributeValues=serialize(
                    {
                        ":choice": question.choice,
                    }
                ),
            )
