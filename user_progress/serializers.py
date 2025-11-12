from rest_framework import serializers
from .models import UserCourse, TestCourseProgress, TestQuestionProgress
from .models import (
    QuizCourseProgress,
    QuizChapterProgress,
    QuizSubtopicProgress,
    QuizQuestionProgress
)
from .models import LatestSubmittedQuizAnalytics, LatestSubmittedTestAnalytics

class UserCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCourse
        fields = ['id', 'course', 'status', 'enrolled_at', 'updated_at']

class QuizQuestionProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestionProgress
        fields = ['id', 'question', 'selected_option', 'is_flagged']


class QuizSubtopicProgressSerializer(serializers.ModelSerializer):
    questions = QuizQuestionProgressSerializer(many=True, read_only=True)

    class Meta:
        model = QuizSubtopicProgress
        fields = ['id', 'subtopic', 'attempted_questions', 'questions']


class QuizChapterProgressSerializer(serializers.ModelSerializer):
    subtopics = QuizSubtopicProgressSerializer(many=True, read_only=True)

    class Meta:
        model = QuizChapterProgress
        fields = ['id', 'chapter', 'attempted_questions', 'subtopics']


class QuizCourseProgressSerializer(serializers.ModelSerializer):
    chapters = QuizChapterProgressSerializer(many=True, read_only=True)
    last_viewed_question = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = QuizCourseProgress
        fields = ['id', 'course', 'attempted_questions', 'flagged_count', 'skipped_count', 'correct_count', 'last_viewed_question', 'is_submitted', 'chapters']

class TestQuestionProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestQuestionProgress
        fields = ['id', 'question', 'selected_option', 'is_flagged']


class TestCourseProgressSerializer(serializers.ModelSerializer):
    questions = TestQuestionProgressSerializer(many=True, read_only=True)
    last_viewed_question = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TestCourseProgress
        fields = ['id', 'course', 'attempted_questions', 'flagged_count', 'skipped_count', 'correct_count', 'last_viewed_question', 'is_submitted', 'questions']

class LatestSubmittedQuizAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LatestSubmittedQuizAnalytics
        fields = ['id', 'course', 'data', 'updated_at']


class LatestSubmittedTestAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LatestSubmittedTestAnalytics
        fields = ['id', 'course', 'data', 'updated_at']
