from django.contrib import admin
from .models import UserCourse, QuizCourseProgress, QuizChapterProgress, QuizSubtopicProgress, QuizQuestionProgress, LatestSubmittedQuizAnalytics, LatestSubmittedTestAnalytics

# Register your models here.
admin.site.register([UserCourse, QuizCourseProgress, QuizChapterProgress, QuizSubtopicProgress, QuizQuestionProgress, LatestSubmittedQuizAnalytics, LatestSubmittedTestAnalytics])