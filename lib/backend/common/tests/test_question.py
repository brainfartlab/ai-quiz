import pytest

from common.question import InvalidAnswer, InvalidQuestion, Question


class TestQuestion:
    @pytest.fixture
    def example_question(self):
        question = Question(
            index=1,
            prompt="What is love?",
            correct_answer="Baby, don't hurt me",
            wrong_answers=[
                "Baby, don't yoghurt me",
                "Chemicals",
            ],
            clarification="Love was first discovered in 1939 in an LSD experiment",
        )

        return question

    def test_create(self, example_question):
        question = Question.create(
            index=1,
            prompt="What is love?",
            correct_answer="Baby, don't hurt me",
            wrong_answers=[
                "Baby, don't yoghurt me",
                "Chemicals",
            ],
            clarification="Love was first discovered in 1939 in an LSD experiment",
        )

        assert question == example_question

    def test_create_invalid(self, example_question):
        with pytest.raises(InvalidQuestion):
            Question.create(
                index=1,
                prompt="What is love?",
                correct_answer="Baby, don't hurt me",
                wrong_answers=[
                    "Baby, don't hurt me",
                    "Baby, don't yoghurt me",
                    "Chemicals",
                ],
                clarification="Love was first discovered in 1939 in an LSD experiment",
            )

    def test_is_answered(self, example_question):
        assert not example_question.is_answered

    def test_answer(self, example_question):
        feedback = example_question.answer("Chemicals")

        assert example_question.is_answered

        assert not feedback.result
        assert feedback.correct_answer == example_question.answer
        assert feedback.clarification == example_question.clarification

    def test_invalid_answer(self, example_question):
        with pytest.raises(InvalidAnswer):
            example_question.answer("Not in the list")

    def test_pose(self, example_question):
        posed_question = example_question.pose()

        assert posed_question["question"] == example_question.prompt
        assert set(posed_question["options"]) == set(
            [example_question.correct_answer, *example_question.wrong_answers]
        )
