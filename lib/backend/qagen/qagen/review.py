from dataclasses import dataclass
from typing import List

from common.game import Game

from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.evaluation.qa import QAEvalChain
from langchain.indexes import VectorstoreIndexCreator
from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter
from langchain.vectorstores import DocArrayInMemorySearch

from ngram import NGram

from .models import QuestionModel as Question


def contains_keyword(text: str, keywords: List[str]) -> bool:
    def key(s):
        return s.lower()

    ng = NGram(text.split(), key=key)

    for keyword in keywords:
        test = ng.searchitem(keyword)
        if test and test[0][1] > 0.5:
            return True

    return False


def is_trivial(game: Game, question: Question) -> bool:
    if contains_keyword(question.answer, game.keywords) and not any(contains_keyword(choice, game.keywords) for choice in question.wrong_answers):
        return True

    return False


@dataclass
class Reviewer:
    openai_token: str

    def review(
        self,
        game: Game,
        questions: List[Question],
        docs: List[Document],
    ) -> List[Question]:
        non_trivial_questions = []
        for question in questions:
            if not is_trivial(game, question):
                non_trivial_questions.append(question)

        temp = [
            {
                "query": question.question,
                "answer": question.answer,
            } for question in non_trivial_questions
        ]

        index = VectorstoreIndexCreator(
            embedding=OpenAIEmbeddings(openai_api_key=self.openai_token),
            text_splitter=TokenTextSplitter(chunk_size=2500, chunk_overlap=0),
            vectorstore_cls=DocArrayInMemorySearch,
        ).from_documents(docs)

        retriever = index.vectorstore.as_retriever()

        llm = ChatOpenAI(openai_api_key=self.openai_token, temperature=0.0)
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
        )
        predictions = qa.apply(temp)

        eval_chain = QAEvalChain.from_llm(llm)
        graded_output = eval_chain.evaluate(temp, predictions)

        final_questions = []
        for i, grade in enumerate(graded_output):
            if grade["text"] == "CORRECT":
                final_questions.append(non_trivial_questions[i])

        return final_questions
