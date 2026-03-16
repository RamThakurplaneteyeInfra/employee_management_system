"""
HR Assessment: questions and answers with per-question answer limit (max 4).
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class Question(models.Model):
    """Assessment question tied to a month and year."""
    question = models.TextField(null=False)
    month = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-12
    year = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'emp_assessment"."hr_assessment_questions'
        verbose_name = "question"
        verbose_name_plural = "questions"
        ordering = ["-year", "-month", "id"]

    def __str__(self):
        return (self.question[:50] + "…") if self.question and len(self.question) > 50 else (self.question or "")


class Answer(models.Model):
    """Answer to a question; at most 4 answers per question."""
    answer = models.TextField(null=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        db_column="question_id",
    )
    score = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'emp_assessment"."hr_assessment_answers'
        verbose_name = "answer"
        verbose_name_plural = "answers"
        ordering = ["question", "id"]

    def __str__(self):
        return (self.answer[:50] + "…") if self.answer and len(self.answer) > 50 else (self.answer or "")

    def clean(self):
        super().clean()
        if not self.question_id:
            return
        # Exclude self when updating so we don't count the current record
        existing = Answer.objects.filter(question_id=self.question_id).exclude(pk=self.pk)
        if existing.count() >= 4:
            raise ValidationError({"question": "A question can have at most 4 answers."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CandidateResponses(models.Model):
    """
    Stores a candidate's selected answer for a given question.
    A candidate can answer the same question multiple times.
    """
    candidate = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        db_column="candidate_id",
        related_name="hr_assessment_responses",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        db_column="question_id",
        related_name="candidate_responses",
    )
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        db_column="answer_id",
        related_name="candidate_responses",
    )
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)

    class Meta:
        db_table = 'emp_assessment"."hr_assessment_candidate_responses'
        verbose_name = "candidate response"
        verbose_name_plural = "candidate responses"
        ordering = ["-date", "-time", "candidate_id"]

    def __str__(self):
        return f"{self.candidate} → Q{self.question_id} / A{self.answer_id}"
