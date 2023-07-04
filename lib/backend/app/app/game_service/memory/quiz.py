import json
from typing import Any, Dict, List

from aws_lambda_powertools import Logger
from langchain.schema import AIMessage, BaseMemory
from pydantic import BaseModel


logger = Logger()


class QuizMemory(BaseMemory, BaseModel):
    """Memory class for storing quiz questions."""

    memory_key: str = "questions"
    questions: List[str] = None

    def clear(self):
        self.questions = None

    @property
    def memory_variables(self) -> List[str]:
        """Define the variables we are providing to the prompt."""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """Load the memory variables, in this case the entity key."""
        # Return combined information about entities to put into context.
        return {self.memory_key: self.questions}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation to buffer."""
        # Get the input text and run through spacy
        questions = []

        for message in inputs["chat_history"]:
            logger.info(message.content)
            if isinstance(message, AIMessage):
                question = json.loads(message.content)
                questions.append(question["prompt"])

        logger.info(questions)
        self.questions = questions
