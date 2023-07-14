from dataclasses import dataclass
from typing import List

from langchain.document_loaders import WikipediaLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.schema import Document
from langchain.text_splitter import TokenTextSplitter
from langchain.vectorstores import DocArrayInMemorySearch


@dataclass
class Researcher:
    openai_token: str

    def research(self, keywords: List[str]) -> List[Document]:
        loader = WikipediaLoader(query=" ".join(keywords))
        wiki_docs = loader.load()

        data = wiki_docs

        index = VectorstoreIndexCreator(
            embedding=OpenAIEmbeddings(openai_api_key=self.openai_token),
            vectorstore_cls=DocArrayInMemorySearch,
            text_splitter=TokenTextSplitter(chunk_size=2500, chunk_overlap=0),
        ).from_documents(data)

        retriever = index.vectorstore.as_retriever()
        relevant_docs = retriever.get_relevant_documents(query=" ".join(keywords))

        return relevant_docs
