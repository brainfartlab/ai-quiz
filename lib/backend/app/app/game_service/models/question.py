from typing import List

from pydantic import BaseModel, Field


class QuestionModel(BaseModel):
    prompt: str = Field(description="The quiz question prompt")
    options: List[str] = Field(
        description="The quiz question answer options, as a list"
    )
    solution: int = Field(
        description="Integer index of the correct option in the options list, starting"
        "from 1"
    )
    clarification: str = Field(
        description="A clarifying answer to the quiz question for informative ends."
        "Include the source of the answer"
    )
