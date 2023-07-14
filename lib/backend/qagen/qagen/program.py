from dataclasses import dataclass
from typing import List

from common.game import Game
from langchain.chat_models import ChatOpenAI
from langchain.evaluation.qa import QAGenerateChain
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from .models import QuestionModel, QuestionsModel


@dataclass
class Programmer:
    openai_token: str

    def program(
        self,
        game: Game,
        docs: List[Document],
    ) -> List[QuestionModel]:
        output_parser = PydanticOutputParser(pydantic_object=QuestionsModel)

        with open("resources/prompt.txt") as f:
            template = f.read()

        prompt = PromptTemplate(
            input_variables=["doc"],
            template=template,
            output_parser=output_parser,
            partial_variables={
                "format_instructions": output_parser.get_format_instructions(),
                "keywords": "\n".join(game.keywords),
            }
        )

        llm = ChatOpenAI(openai_api_key=self.openai_token, temperature=0.0)
        qa_chain = QAGenerateChain(
            llm=llm,
            prompt=prompt,
        )

        results = qa_chain.apply(
            [
                {"doc": doc} for doc in docs
            ]
        )

        questions = []
        for result in results:
            doc_questions = output_parser.parse(result["text"])
            questions.extend(doc_questions.questions)

        return questions
