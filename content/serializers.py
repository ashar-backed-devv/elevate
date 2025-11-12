from rest_framework import serializers
from .models import Domain, Course, Announcement, Chapter, Subtopic, Flashcard, Question
from user_progress.models import UserCourse

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name', 'created_at', 'updated_at']

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'domain', 'name', 'about_primary', 'about_secondary', 'total_questions', 'total_chapters', 'created_at', 'updated_at']

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'course', 'primary_text', 'secondary_text', 'created_at']

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'course', 'name', 'created_at', 'updated_at']

class SubtopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtopic
        fields = ['id', 'chapter', 'name', 'created_at', 'updated_at']

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ['id', 'subtopic', 'primary_text', 'secondary_text', 'created_at', 'updated_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'subtopic', 'text', 'option0', 'option1', 'option2', 'option3', 'correct_option', 'explanation', 'created_at', 'updated_at']

# For Dashboard:

class SimpleCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']


class DomainWithCoursesSerializer(serializers.ModelSerializer):
    currently_studying = serializers.SerializerMethodField()
    course_library = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = ['id', 'name', 'currently_studying', 'course_library']

    def get_currently_studying(self, obj):
        user = self.context['request'].user

        # Get user’s enrolled courses ordered by most recent enrollment first
        enrolled_courses = (
            UserCourse.objects
            .filter(user=user, course__domain=obj)
            .select_related('course')
            .order_by('-enrolled_at')  # newest first
        )

        # Extract the actual Course objects in the sorted order
        courses = [uc.course for uc in enrolled_courses]
        return SimpleCourseSerializer(courses, many=True).data


    def get_course_library(self, obj):
        user = self.context['request'].user
        enrolled_course_ids = UserCourse.objects.filter(
            user=user
        ).values_list('course_id', flat=True)

        courses = obj.courses.exclude(id__in=enrolled_course_ids)
        return SimpleCourseSerializer(courses, many=True).data


# For Course Details:

# Subtopic
class SubtopicMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtopic
        fields = ['id', 'name']

# Chapter with nested Subtopics
class ChapterWithSubtopicsSerializer(serializers.ModelSerializer):
    subtopics = SubtopicMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'name', 'subtopics']

# Announcement
class AnnouncementMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'primary_text', 'secondary_text', 'created_at']

# Course with Announcements and Chapters
class CourseDetailSerializer(serializers.ModelSerializer):
    announcements = serializers.SerializerMethodField()
    chapters = ChapterWithSubtopicsSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'name',
            'about_primary',
            'about_secondary',
            'total_questions',
            'total_chapters',
            'announcements',
            'chapters'
        ]

    def get_announcements(self, obj):
        announcements = obj.announcements.order_by('-created_at')  # latest first
        return AnnouncementMiniSerializer(announcements, many=True).data

# For Quiz/Exam/Questions Page:

class QuestionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'option0', 'option1', 'option2', 'option3', 'correct_option', 'explanation']


class SubtopicWithQuestionsSerializer(serializers.ModelSerializer):
    questions = QuestionMiniSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Subtopic
        fields = ['id', 'name', 'question_count', 'questions']

    def get_question_count(self, obj):
        return obj.questions.count()


class ChapterWithSubtopicsSerializer(serializers.ModelSerializer):
    subtopics = SubtopicWithQuestionsSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'name', 'subtopics']


class CourseQuestionDetailSerializer(serializers.ModelSerializer):
    chapters = ChapterWithSubtopicsSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'total_questions', 'chapters']
    
    def get_total_questions(self, obj):
        return Question.objects.filter(subtopic__chapter__course=obj).count()


# For Flashcards Page:

class FlashcardNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ['id', 'primary_text', 'secondary_text']


class SubtopicNestedSerializer(serializers.ModelSerializer):
    flashcards = FlashcardNestedSerializer(many=True, read_only=True)
    flashcard_count = serializers.SerializerMethodField()

    class Meta:
        model = Subtopic
        fields = ['id', 'name', 'flashcard_count', 'flashcards']

    def get_flashcard_count(self, obj):
        return obj.flashcards.count()


class ChapterNestedSerializer(serializers.ModelSerializer):
    subtopics = SubtopicNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'name', 'subtopics']


class CourseFlashcardDetailSerializer(serializers.ModelSerializer):
    chapters = ChapterNestedSerializer(many=True, read_only=True)
    total_flashcards = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'total_flashcards', 'chapters']

    def get_total_flashcards(self, obj):
        # Count all flashcards in this course
        return Flashcard.objects.filter(subtopic__chapter__course=obj).count()
