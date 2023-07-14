import json
import os
import random
from typing import List, Set

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent

from common.game import Game, GameStatus
from common.gateway import AmazonGateway
from common.player import Player
from common.question import Question


from .program import Programmer
from .research import Researcher
from .review import Reviewer


tracer = Tracer()
logger = Logger()


def initialize():
    global gateway

    gateway = AmazonGateway(
        game_queue=None,
        game_table=os.getenv("GAME_TABLE"),
        question_table=os.getenv("QUESTION_TABLE"),
        token_table=None,
        openai_secret=os.getenv("OPENAI_API_KEY_SECRET"),
    )


initialize()


def design_game(game: Game, openai_token: str) -> List[Question]:
    researcher = Researcher(openai_token=openai_token)
    logger.info(f"researching for keywords: {game.keywords}")
    docs = researcher.research(game.keywords)
    logger.info(f"research yielded {len(docs)} documents")

    programmer = Programmer(openai_token=openai_token)
    logger.info("programming questions")
    initial_questions = programmer.program(game, docs)
    logger.info(f"programming yielded {len(initial_questions)} questions")

    reviewer = Reviewer(openai_token=openai_token)
    logger.info("reviewing questions")
    final_questions = reviewer.review(game, initial_questions, docs)
    logger.info(f"reviewing yielded {len(final_questions)} questions")

    if len(final_questions) > game.questions_limit:
        logger.info(f"sampling {game.questions_limit} questions")
        final_questions = random.sample(final_questions, game.questions_limit)

    return [
        Question.create(
            index=i+1,
            prompt=question.question,
            correct_answer=question.answer,
            wrong_answers=question.wrong_answers,
            clarification=question.clarification,
        ) for i, question in enumerate(final_questions)
    ]


@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context):
    global gateway

    openai_token = gateway.get_openai_token()

    for record in event.records:
        data = json.loads(record.body)

        logger.info("looking up player and game")
        player = Player(data["player_id"])
        game = gateway.get_game(player, data["game_id"])

        questions = design_game(game, openai_token)

        logger.info("storing questions")
        gateway.store_game_questions(game, questions)
        logger.info("updating game status")
        game.game_status = GameStatus.READY
        print(questions)
        gateway.update_game_status(player, game)
