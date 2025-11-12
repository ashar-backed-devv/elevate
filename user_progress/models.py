from django.db import models
from django.conf import settings
from content.models import Course, Chapter, Subtopic, Question  # Import from content app

class UserCourse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='studying')  # e.g., 'studying', 'completed'
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user} - {self.course.name}"

# Quiz progress (course -> chapter -> subtopic -> question)
class QuizCourseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    attempted_questions = models.PositiveIntegerField(default=0)
    flagged_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    last_viewed_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.name}"


class QuizChapterProgress(models.Model):
    course_progress = models.ForeignKey(QuizCourseProgress, on_delete=models.CASCADE, related_name='chapters')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    attempted_questions = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('course_progress', 'chapter')

    def __str__(self):
        return f"Chapter: {self.chapter.name}"


class QuizSubtopicProgress(models.Model):
    chapter_progress = models.ForeignKey(QuizChapterProgress, on_delete=models.CASCADE, related_name='subtopics')
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE)
    attempted_questions = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('chapter_progress', 'subtopic')

    def __str__(self):
        return f"Subtopic: {self.subtopic.name}"


class QuizQuestionProgress(models.Model):
    subtopic_progress = models.ForeignKey(QuizSubtopicProgress, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)

    class Meta:
        unique_together = ('subtopic_progress', 'question')

    def __str__(self):
        return f"Question {self.question.id} progress"

# Full-test progress (course -> questions) — no chapters/subtopics
class TestCourseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    attempted_questions = models.PositiveIntegerField(default=0)
    flagged_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    last_viewed_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"Full Test Progress: {self.user.username} - {self.course.name}"


class TestQuestionProgress(models.Model):
    course_progress = models.ForeignKey(TestCourseProgress, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)

    class Meta:
        unique_together = ('course_progress', 'question')

    def __str__(self):
        return f"Test Question Progress: {self.question.id}"


class LatestSubmittedQuizAnalytics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='latest_quiz_analytics')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)  # store full nested progress snapshot
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"Latest Quiz Analytics: {self.user.username} - {self.course.name}"


class LatestSubmittedTestAnalytics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='latest_test_analytics')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"Latest Test Analytics: {self.user.username} - {self.course.name}"
