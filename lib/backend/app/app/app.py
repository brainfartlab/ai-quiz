import hashlib
import json
import os
import urllib

from auth0.authentication import Users
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayHttpResolver,
    Response,
    content_types,
)
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError,
    ServiceError,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3

from .game import Game, InvalidGame, QuestionsLimitReached
from .game_service import OpenAIService
from .gateway import DynamoGateway, NoSuchGame, NoSuchQuestion, UnknownToken
from .player import Player


tracer = Tracer()
logger = Logger()
app = APIGatewayHttpResolver()


def initialize():
    global gateway, service

    secrets_client = boto3.client("secretsmanager")
    openai_key = secrets_client.get_secret_value(
        SecretId=os.getenv("OPENAI_API_KEY_SECRET")
    )

    gateway = DynamoGateway(
        game_table=os.getenv("GAME_TABLE"),
        question_table=os.getenv("QUESTION_TABLE"),
        token_table=is.getenv("TOKEN_TABLE"),
    )
    service = OpenAIService(
        api_key=openai_key["SecretString"],
        session_table=os.getenv("SESSION_TABLE"),
    )


initialize()


@app.get("/games")
@tracer.capture_method
def get_games():
    player = get_player(app.current_event)
    games = gateway.list_player_games(player.player_id)

    return {"games": [game.to_dict() for game in games]}


@app.post("/games")
@tracer.capture_method
def start_game():
    global gateway

    json_payload = app.current_event.json_body

    player = get_player(app.current_event)
    game = Game.create(
        keywords=set(json_payload["keywords"]),
        questions_limit=15,
    )

    gateway.store_game(player.player_id, game)
    return game.to_dict()


@app.get("/games/<game>")
@tracer.capture_method
def get_game(game):
    global gateway

    player = get_player(app.current_event)
    game = gateway.get_game(player.player_id, game)

    return game.to_dict()


@app.get("/games/<game>/questions")
@tracer.capture_method
def get_questions(game):
    global gateway

    player = get_player(app.current_event)
    game = gateway.get_game(player.player_id, game)

    return {
        "questions": [
            {
                "prompt": question.prompt,
                "solution": question.solution_str,
                "result": question.answered_correctly,
            }
            if question.is_answered
            else {
                "prompt": question.prompt,
            }
            for question in game.questions
        ]
    }


@app.post("/games/<game>/questions/ask")
@tracer.capture_method
def generate_question(game):
    global gateway, service

    player = get_player(app.current_event)
    game = gateway.get_game(player.player_id, game)

    question = game.quiz(service)
    gateway.update_game(player.player_id, game)

    return {
        "prompt": question.prompt,
        "options": question.options,
    }


@app.get("/games/<game>/questions/<question>")
@tracer.capture_method
def get_question(game, question):
    global gateway

    player = get_player(app.current_event)
    game = gateway.get_game(player.player_id, game)
    question = question.get_game_question(game, question)

    return {
        "question": question.prompt,
        "options": question.options,
    }


@app.post("/games/<game>/questions/answer")
@tracer.capture_method
def answer_question(game):
    global gateway

    json_payload = app.current_event.json_body

    player = get_player(app.current_event)
    game = gateway.get_game(player.player_id, game)

    question = game.quiz(service)
    feedback = question.answer(json_payload["choice"])

    gateway.update_game(player.player_id, game)

    return {
        "result": feedback.result,
        "solution": feedback.solution,
        "clarification": feedback.clarification,
    }


@app.exception_handler(NoSuchGame)
def handle_game_not_found(ex: NoSuchGame):
    raise NotFoundError


@app.exception_handler(NoSuchQuestion)
def handle_question_not_found(ex: NoSuchQuestion):
    raise NotFoundError


@app.exception_handler(InvalidGame)
def handle_invalid_game(ex: InvalidGame):
    return Response(
        status_code=400,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(ex.to_json()),
    )


@app.exception_handler(QuestionsLimitReached)
def handle_questions_limit_reached(ex: QuestionsLimitReached):
    game_id = ex.game.game_id
    questions_limit = ex.game.questions_limit

    return Response(
        status_code=400,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(
            {
                "errors": [
                    {
                        "message": f"Game {game_id} has reached questions limit of {questions_limit}",
                    }
                ]
            }
        ),
    )


def hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_player(event) -> Player:
    global gateway

    domain = urllib.parse.urlparse(event.request_context.authorizer.jwt_claim["iss"])
    token = event.get_header_value("Authorization").split(" ")[-1]

    try:
        return gateway.get_player_by_token(token)
    except UnknownToken:
        users = Users(domain.netloc)
        user = users.userinfo(token)

        player_id = hash(user["email"])
        player = Player(player_id)
        gateway.store_player_by_token(token, player)

        return player


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
