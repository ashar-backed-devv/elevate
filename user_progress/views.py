from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import UserCourse, QuizCourseProgress, QuizChapterProgress, QuizSubtopicProgress, QuizQuestionProgress, TestCourseProgress, TestQuestionProgress
from .serializers import UserCourseSerializer, QuizCourseProgressSerializer, TestCourseProgressSerializer
from django.db import transaction
from content.models import Course, Chapter, Subtopic, Question
from .models import (
    LatestSubmittedQuizAnalytics,
    LatestSubmittedTestAnalytics,
)
from .serializers import (
    LatestSubmittedQuizAnalyticsSerializer,
    LatestSubmittedTestAnalyticsSerializer,
    QuizCourseProgressSerializer,
    TestCourseProgressSerializer,
)


class UserCourseViewSet(viewsets.ModelViewSet):
    serializer_class = UserCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserCourse.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# For tracking and managing quiz/test progress and analytics:

class QuizCourseProgressViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    @transaction.atomic
    def progress(self, request, pk=None):
        """
        GET /.../quiz-course-progress/{course_id}/progress/?source=content|analytics
        source=analytics  -> return progress even if submitted
        source=content    -> if submitted: reset to initialized state and return fresh progress
        """
        user = request.user
        source = request.query_params.get('source', 'content')  # 'content' or 'analytics'
        course = Course.objects.get(pk=pk)

        course_progress, created = QuizCourseProgress.objects.get_or_create(user=user, course=course)

        if created:
            # initialize nested progress
            for chapter in course.chapters.all():
                chap_prog = QuizChapterProgress.objects.create(course_progress=course_progress, chapter=chapter)
                for subtopic in chapter.subtopics.all():
                    sub_prog = QuizSubtopicProgress.objects.create(chapter_progress=chap_prog, subtopic=subtopic)
                    for question in subtopic.questions.all():
                        QuizQuestionProgress.objects.create(subtopic_progress=sub_prog, question=question)
            serializer = QuizCourseProgressSerializer(course_progress)
            return Response(serializer.data)

        # if exists and submitted
        if course_progress.is_submitted:
            if source == 'analytics':
                serializer = QuizCourseProgressSerializer(course_progress)
                return Response(serializer.data)
            else:
                # reset existing progress in-place (preserve DB record for analytics reads)
                # reset attempted counters and question states
                course_progress.attempted_questions = 0
                course_progress.flagged_count = 0
                course_progress.skipped_count = 0
                course_progress.correct_count = 0
                course_progress.last_viewed_question = None
                course_progress.is_submitted = False
                course_progress.save(update_fields=['attempted_questions', 'is_submitted', 'last_viewed_question', 'correct_count', 'skipped_count', 'flagged_count', 'updated_at'])

                for chap_prog in course_progress.chapters.all():
                    chap_prog.attempted_questions = 0
                    chap_prog.save(update_fields=['attempted_questions'])
                    for sub_prog in chap_prog.subtopics.all():
                        sub_prog.attempted_questions = 0
                        sub_prog.save(update_fields=['attempted_questions'])
                        for q_prog in sub_prog.questions.all():
                            q_prog.selected_option = None
                            q_prog.is_flagged = False
                            q_prog.save(update_fields=['selected_option', 'is_flagged'])

                serializer = QuizCourseProgressSerializer(course_progress)
                return Response(serializer.data)

        # not submitted -> just return
        serializer = QuizCourseProgressSerializer(course_progress)
        return Response(serializer.data)


    @action(detail=False, methods=['post'])
    @transaction.atomic
    def update_question(self, request):
        """
        POST payload:
        {
            "question_id": int,
            "selected_option": int|null,
            "is_flagged": bool
        }
        Updates progress with flagged, skipped, and correct counters.
        """
        user = request.user
        question_id = request.data.get('question_id')
        selected_option = request.data.get('selected_option')
        is_flagged = request.data.get('is_flagged')

        try:
            question = Question.objects.get(pk=question_id)
            subtopic = question.subtopic
            chapter = subtopic.chapter
            course = chapter.course

            course_prog = QuizCourseProgress.objects.get(user=user, course=course)

            if course_prog.is_submitted:
                return Response({'error': 'progress already submitted; reinitialize first'}, status=status.HTTP_400_BAD_REQUEST)

            chapter_prog = course_prog.chapters.get(chapter=chapter)
            subtopic_prog = chapter_prog.subtopics.get(subtopic=subtopic)
            question_prog = subtopic_prog.questions.get(question=question)

            # Previous state
            prev_selected = question_prog.selected_option
            prev_flagged = question_prog.is_flagged
            prev_correct = prev_selected == question.correct_option if prev_selected is not None else False
            prev_skipped = prev_selected is None

            # Current state
            curr_selected = selected_option
            curr_flagged = is_flagged
            curr_correct = curr_selected == question.correct_option if curr_selected is not None else False
            curr_skipped = curr_selected is None

            # Update flagged counter
            if not prev_flagged and curr_flagged:
                course_prog.flagged_count += 1
            elif prev_flagged and not curr_flagged:
                course_prog.flagged_count -= 1

            # Update skipped counter
            if prev_skipped and not curr_skipped:
                course_prog.skipped_count -= 1
            elif not prev_skipped and curr_skipped:
                course_prog.skipped_count += 1

            # Update correct counter
            if not prev_correct and curr_correct:
                course_prog.correct_count += 1
            elif prev_correct and not curr_correct:
                course_prog.correct_count -= 1

            # Update attempted count (as before)
            was_attempted = prev_selected is not None
            is_now_attempted = curr_selected is not None

            if not was_attempted and is_now_attempted:
                subtopic_prog.attempted_questions += 1
                chapter_prog.attempted_questions += 1
                course_prog.attempted_questions += 1
            elif was_attempted and not is_now_attempted:
                subtopic_prog.attempted_questions -= 1
                chapter_prog.attempted_questions -= 1
                course_prog.attempted_questions -= 1

            # Save question state
            question_prog.selected_option = curr_selected
            question_prog.is_flagged = curr_flagged
            question_prog.save(update_fields=['selected_option', 'is_flagged'])

            subtopic_prog.save(update_fields=['attempted_questions'])
            chapter_prog.save(update_fields=['attempted_questions'])
            course_prog.last_viewed_question = question
            course_prog.save(update_fields=[
                'attempted_questions', 'flagged_count',
                'skipped_count', 'correct_count',
                'last_viewed_question', 'updated_at'
            ])

            return Response({'status': 'progress updated'}, status=status.HTTP_200_OK)

        except Question.DoesNotExist:
            return Response({'error': 'Invalid question ID'}, status=status.HTTP_400_BAD_REQUEST)
        except QuizCourseProgress.DoesNotExist:
            return Response({'error': 'no initialized progress; call GET progress first'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        """
        Marks progress as submitted and stores snapshot to LatestQuizAnalytics.
        """
        user = request.user
        try:
            course_progress = QuizCourseProgress.objects.get(user=user, course_id=pk)
            course_progress.is_submitted = True
            course_progress.save(update_fields=['is_submitted', 'updated_at'])

            # serialize current nested progress
            serialized = QuizCourseProgressSerializer(course_progress).data

            # store/update latest analytics
            LatestSubmittedQuizAnalytics.objects.update_or_create(
                user=user, course_id=pk,
                defaults={'data': serialized}
            )

            return Response({'status': 'progress submitted and analytics updated'}, status=status.HTTP_200_OK)
        except QuizCourseProgress.DoesNotExist:
            return Response({'error': 'no active progress'}, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['get'], url_path='is_submitted')
    def check_submission_status(self, request, pk=None):
        """
        Returns whether the quiz/test has been submitted or not.
        Example: /api/quiz-course-progress/1/is_submitted/
        """
        user = request.user
        course_id = pk

        progress = QuizCourseProgress.objects.filter(user=user, course_id=course_id).first()
        is_submitted = progress.is_submitted if progress else False

        return Response({
            'course_id': course_id,
            'is_submitted': is_submitted
        })


    @action(detail=True, methods=['get'], url_path='latest-submitted-analytics')
    def get_latest_submitted_analytics(self, request, pk=None):
        """
        Returns the latest submitted quiz analytics for this course.
        """
        user = request.user
        analytics = LatestSubmittedQuizAnalytics.objects.filter(user=user, course_id=pk).first()
        if not analytics:
            return Response({'detail': 'No analytics found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LatestSubmittedQuizAnalyticsSerializer(analytics)
        return Response(serializer.data)
    

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def quit(self, request, pk=None):
        """
        When user quits mid-quiz — delete current progress.
        """
        user = request.user
        QuizCourseProgress.objects.filter(user=user, course_id=pk).delete()
        return Response({'status': 'quiz progress reset to default'}, status=status.HTTP_200_OK)


class TestCourseProgressViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    @transaction.atomic
    def progress(self, request, pk=None):
        """
        GET /.../test-course-progress/{course_id}/progress/?source=content|analytics
        Behavior same as quiz progress but for test (no chapters/subtopics)
        """
        user = request.user
        source = request.query_params.get('source', 'content')
        course = Course.objects.get(pk=pk)
        course_progress, created = TestCourseProgress.objects.get_or_create(user=user, course=course)

        if created:
            questions = Question.objects.filter(subtopic__chapter__course=course)
            for q in questions:
                TestQuestionProgress.objects.create(course_progress=course_progress, question=q)
            serializer = TestCourseProgressSerializer(course_progress)
            return Response(serializer.data)

        if course_progress.is_submitted:
            if source == 'analytics':
                serializer = TestCourseProgressSerializer(course_progress)
                return Response(serializer.data)
            else:
                # reset in-place
                course_progress.attempted_questions = 0
                course_progress.flagged_count = 0
                course_progress.skipped_count = 0
                course_progress.correct_count = 0
                course_progress.last_viewed_question = None
                course_progress.is_submitted = False
                course_progress.save(update_fields=['attempted_questions', 'is_submitted', 'last_viewed_question', 'correct_count', 'skipped_count', 'flagged_count', 'updated_at'])

                for q_prog in course_progress.questions.all():
                    q_prog.selected_option = None
                    q_prog.is_flagged = False
                    q_prog.save(update_fields=['selected_option', 'is_flagged'])
                serializer = TestCourseProgressSerializer(course_progress)
                return Response(serializer.data)

        serializer = TestCourseProgressSerializer(course_progress)
        return Response(serializer.data)


    @action(detail=False, methods=['post'])
    @transaction.atomic
    def update_question(self, request):
        """
        POST payload:
        {
            "question_id": int,
            "selected_option": int|null,
            "is_flagged": bool
        }
        Updates flagged_count, skipped_count, correct_count.
        """
        user = request.user
        question_id = request.data.get('question_id')
        selected_option = request.data.get('selected_option')
        is_flagged = request.data.get('is_flagged')

        try:
            question = Question.objects.get(pk=question_id)
            course = question.subtopic.chapter.course
            course_prog = TestCourseProgress.objects.get(user=user, course=course)

            if course_prog.is_submitted:
                return Response({'error': 'progress already submitted; reinitialize first'}, status=status.HTTP_400_BAD_REQUEST)

            question_prog = course_prog.questions.get(question=question)

            # Previous state
            prev_selected = question_prog.selected_option
            prev_flagged = question_prog.is_flagged
            prev_correct = prev_selected == question.correct_option if prev_selected is not None else False
            prev_skipped = prev_selected is None

            # Current state
            curr_selected = selected_option
            curr_flagged = is_flagged
            curr_correct = curr_selected == question.correct_option if curr_selected is not None else False
            curr_skipped = curr_selected is None

            # Update flagged counter
            if not prev_flagged and curr_flagged:
                course_prog.flagged_count += 1
            elif prev_flagged and not curr_flagged:
                course_prog.flagged_count -= 1

            # Update skipped counter
            if prev_skipped and not curr_skipped:
                course_prog.skipped_count -= 1
            elif not prev_skipped and curr_skipped:
                course_prog.skipped_count += 1

            # Update correct counter
            if not prev_correct and curr_correct:
                course_prog.correct_count += 1
            elif prev_correct and not curr_correct:
                course_prog.correct_count -= 1

            # Update attempted count
            was_attempted = prev_selected is not None
            is_now_attempted = curr_selected is not None

            if not was_attempted and is_now_attempted:
                course_prog.attempted_questions += 1
            elif was_attempted and not is_now_attempted:
                course_prog.attempted_questions -= 1

            # Save question and course
            question_prog.selected_option = curr_selected
            question_prog.is_flagged = curr_flagged
            question_prog.save(update_fields=['selected_option', 'is_flagged'])

            course_prog.last_viewed_question = question
            course_prog.save(update_fields=[
                'attempted_questions', 'flagged_count',
                'skipped_count', 'correct_count',
                'last_viewed_question', 'updated_at'
            ])

            return Response({'status': 'progress updated'}, status=status.HTTP_200_OK)

        except Question.DoesNotExist:
            return Response({'error': 'Invalid question ID'}, status=status.HTTP_400_BAD_REQUEST)
        except TestCourseProgress.DoesNotExist:
            return Response({'error': 'no initialized progress; call GET progress first'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        """
        Marks test progress as submitted and stores snapshot to LatestTestAnalytics.
        """
        user = request.user
        try:
            course_progress = TestCourseProgress.objects.get(user=user, course_id=pk)
            course_progress.is_submitted = True
            course_progress.save(update_fields=['is_submitted', 'updated_at'])

            serialized = TestCourseProgressSerializer(course_progress).data

            LatestSubmittedTestAnalytics.objects.update_or_create(
                user=user, course_id=pk,
                defaults={'data': serialized}
            )

            return Response({'status': 'progress submitted and analytics updated'}, status=status.HTTP_200_OK)
        except TestCourseProgress.DoesNotExist:
            return Response({'error': 'no active progress'}, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['get'], url_path='is_submitted')
    def check_submission_status(self, request, pk=None):
        """
        Returns whether the quiz/test has been submitted or not.
        Example: /api/test-course-progress/1/is_submitted/
        """
        user = request.user
        course_id = pk

        progress = TestCourseProgress.objects.filter(user=user, course_id=course_id).first()
        is_submitted = progress.is_submitted if progress else False

        return Response({
            'course_id': course_id,
            'is_submitted': is_submitted
        })


    @action(detail=True, methods=['get'], url_path='latest-submitted-analytics')
    def get_latest_submitted_analytics(self, request, pk=None):
        """
        Returns the latest submitted test analytics for this course.
        """
        user = request.user
        analytics = LatestSubmittedTestAnalytics.objects.filter(user=user, course_id=pk).first()
        if not analytics:
            return Response({'detail': 'No analytics found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LatestSubmittedTestAnalyticsSerializer(analytics)
        return Response(serializer.data)


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def quit(self, request, pk=None):
        """
        When user quits mid-test — delete current progress.
        """
        user = request.user
        TestCourseProgress.objects.filter(user=user, course_id=pk).delete()
        return Response({'status': 'test progress reset to default'}, status=status.HTTP_200_OK)