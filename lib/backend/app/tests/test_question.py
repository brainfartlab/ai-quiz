import pytest

from app.question import InvalidAnswer, InvalidQuestion, Question


class TestQuestion:
    @pytest.fixture
    def example_question(self):
        question = Question(
            prompt="What is love?",
            options=[
                "Baby, don't hurt me",
                "Chemicals",
            ],
            clarification="Love was first discovered in 1939 in an LSD experiment",
            solution=1,
        )

        return question

    def test_create(self, example_question):
        question = Question.create(
            prompt="What is love?",
            options=[
                "Baby, don't hurt me",
                "Chemicals",
            ],
            clarification="Love was first discovered in 1939 in an LSD experiment",
            solution=1,
        )

        assert question == example_question

    def test_create_invalid(self, example_question):
        with pytest.raises(InvalidQuestion):
            Question.create(
                prompt="What is love?",
                options=[
                    "Baby, don't hurt me",
                    "Chemicals",
                ],
                clarification="Love was first discovered in 1939 in an LSD experiment",
                solution=0,
            )

    def test_is_answered(self, example_question):
        assert not example_question.is_answered

    def test_answer(self, example_question):
        feedback = example_question.answer(1)

        assert example_question.is_answered

        assert feedback.result
        assert feedback.solution == example_question.solution
        assert feedback.clarification == example_question.clarification

    def test_invalid_answer(self, example_question):
        with pytest.raises(InvalidAnswer):
            example_question.answer(3)

        with pytest.raises(InvalidAnswer):
            example_question.answer(0)

    def test_pose(self, example_question):
        assert example_question.pose() == {
            "question": example_question.prompt,
            "options": example_question.options,
        }
