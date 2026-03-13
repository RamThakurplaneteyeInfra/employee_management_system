"""
HR Assessment: questions and answers with per-question answer limit (max 4).
"""
from django.db import models
from django.core.exceptions import ValidationError


class Question(models.Model):
    """Assessment question tied to a month and year."""
    question = models.TextField(null=False)
    month = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-12
    year = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hr_assessment_questions"
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
        db_table = "hr_assessment_answers"
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
