from dataclasses import dataclass, field

from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.memory import (
    CombinedMemory,
    ConversationBufferMemory,
)
from langchain.memory.chat_message_histories import DynamoDBChatMessageHistory
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import BaseMemory

from .base import BaseGameService
from .memory import QuizMemory
from .models import QuestionModel
from ..game import Game
from ..question import Question


@dataclass
class OpenAIService(BaseGameService):
    api_key: str
    session_table: str

    llm: BaseChatModel = field(init=False)
    parser: PydanticOutputParser = field(init=False)
    prompt: ChatPromptTemplate = field(init=False)

    def __post_init__(self):
        parser = PydanticOutputParser(pydantic_object=QuestionModel)

        with open("resources/langchain/prompts/system.txt") as f:
            llm = ChatOpenAI(temperature=0.9, openai_api_key=self.api_key)
            system_prompt = SystemMessagePromptTemplate.from_template(f.read())

            prompt = ChatPromptTemplate(
                messages=[
                    system_prompt,
                ],
                input_variables=["keywords", "questions", "input"],
                partial_variables={
                    "format_instructions": parser.get_format_instructions(),
                },
            )

            self.llm = llm
            self.parser = parser
            self.prompt = prompt

    def get_memory(self, game_id: str) -> BaseMemory:
        message_history = DynamoDBChatMessageHistory(
            table_name=self.session_table,
            session_id=game_id,
        )

        chat_memory = ConversationBufferMemory(
            memory_key="chat_history",
            chat_memory=message_history,
            return_messages=True,
            input_key="input",
        )

        quiz_memory = QuizMemory(input_key="chat_history")

        return CombinedMemory(memories=[chat_memory, quiz_memory])

    def generate_question(self, game: Game) -> Question:
        chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.get_memory(game.game_id),
        )

        output = chain.run(
            input="Generate a new question",
            keywords=", ".join(game.keywords),
        )
        question_data = self.parser.parse(output)

        question = Question.create(
            prompt=question_data.prompt,
            options=question_data.options,
            clarification=question_data.clarification,
            solution=question_data.solution,
        )

        return question
