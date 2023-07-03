import json
import os
from typing import List

from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import DynamoDBChatMessageHistory
from langchain.output_parsers import (
    PydanticOutputParser,
    ResponseSchema,
    StructuredOutputParser,
)
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

from .base import BaseGameService
from ..game import Game
from ..question import Question


PARAM_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PARAM_SESSION_TABLE = os.getenv("SESSION_TABLE")


class QuestionModel(BaseModel):
    prompt: str = Field(description="The quiz question")
    options: List[str] = Field(
        description="The quiz question answer options, as a list"
    )
    solution: int = Field(
        description="Integer index of the correct option in the options list, starting"
        "from 1"
    )
    clarification: str = Field(
        description="A clarifying answer to the quiz question for informative ends"
    )


class OpenAIService(BaseGameService):
    def get_output_parser(self) -> PydanticOutputParser:
        parser = PydanticOutputParser(pydantic_object=QuestionModel)

        return parser

    def get_output_parser_old(self) -> StructuredOutputParser:
        with open("resources/langchain/schemas/question.json") as f:
            schema = json.load(f)

            return StructuredOutputParser.from_response_schemas(
                [
                    ResponseSchema(
                        name=i["field"],
                        description=i["description"],
                    )
                    for i in schema
                ]
            )

    def get_prompt(self, output_parser) -> ChatPromptTemplate:
        with open("resources/langchain/prompts/system.txt") as f:
            system_prompt = SystemMessagePromptTemplate.from_template(f.read())
            human_prompt = HumanMessagePromptTemplate.from_template(
                "{format_instructions}\nKeywords: {keywords}"
            )

            prompt = ChatPromptTemplate(
                messages=[
                    system_prompt,
                    human_prompt,
                ],
                input_variables=["keywords"],
                partial_variables={
                    "format_instructions": output_parser.get_format_instructions(),
                },
            )

            return prompt

    def get_llm(self) -> BaseChatModel:
        return ChatOpenAI(temperature=0.9, openai_api_key=PARAM_OPENAI_API_KEY)

    def get_memory(self, game_id: str) -> ConversationBufferMemory:
        message_history = DynamoDBChatMessageHistory(
            table_name=PARAM_SESSION_TABLE, session_id=game_id
        )

        return ConversationBufferMemory(
            memory_key="chat_history",
            chat_memory=message_history,
            return_messages=True,
        )

    def generate_question(self, game: Game) -> Question:
        output_parser = self.get_output_parser()

        chain = LLMChain(
            llm=self.get_llm(),
            prompt=self.get_prompt(output_parser),
            memory=self.get_memory(game.game_id),
        )

        output = chain.run(", ".join(game.keywords))
        question_data = output_parser.parse(output)

        question = Question.create(
            prompt=question_data.prompt,
            options=question_data.options,
            clarification=question_data.clarification,
            solution=question_data.solution,
        )

        return question
