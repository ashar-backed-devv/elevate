from rest_framework import viewsets, permissions
from .models import Domain, Course, Announcement, Chapter, Subtopic, Flashcard, Question
from .serializers import DomainSerializer, CourseSerializer, AnnouncementSerializer, ChapterSerializer, SubtopicSerializer, FlashcardSerializer, QuestionSerializer, DomainWithCoursesSerializer, CourseDetailSerializer, CourseQuestionDetailSerializer, CourseFlashcardDetailSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response

# Custom permission to allow read for authenticated users, write for admins only
class AdminWriteOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Allow POST, PUT, DELETE for admins only
        return request.user and (request.user.is_staff or request.user.is_superuser)

class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [AdminWriteOrReadOnly]  # Admin-only writes, authenticated reads

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def courses(self, request):
        """
        Returns all domains with their courses (id, name).
        Example: /api/domains/courses/
        """
        domains = Domain.objects.prefetch_related('courses').all()
        response_data = []

        for domain in domains:
            courses = list(domain.courses.all().values('id', 'name'))
            response_data.append({
                'id': domain.id,
                'name': domain.name,
                'courses': courses
            })

        return Response(response_data)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AdminWriteOrReadOnly]

    # For Questions Page:
    @action(detail=True, methods=['get'], url_path='question_page')
    def question_details(self, request, pk=None):
        course = self.get_object()
        serializer = CourseQuestionDetailSerializer(course)
        return Response(serializer.data)

    # For Flashcards Page:
    @action(detail=True, methods=['get'], url_path='flashcard_page')
    def flashcard_details(self, request, pk=None):
        course = self.get_object()
        serializer = CourseFlashcardDetailSerializer(course)
        return Response(serializer.data)

    # For Mock Exams/Full Test Page:
    @action(detail=True, methods=['get'], url_path='full_test_page')
    def questions(self, request, pk=None):
        """
        Returns all questions linked to a specific course.
        Example: /api/courses/1/questions/
        """
        course = self.get_object()

        # Fetch all questions where the subtopic's chapter belongs to this course
        questions = Question.objects.filter(subtopic__chapter__course=course).values(
            'id', 'text', 'option0', 'option1', 'option2', 'option3', 'correct_option', 'explanation'
        )

        return Response({
            'total_questions': questions.count(),
            'questions': list(questions)
        })


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [AdminWriteOrReadOnly]

class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [AdminWriteOrReadOnly]

class SubtopicViewSet(viewsets.ModelViewSet):
    queryset = Subtopic.objects.all()
    serializer_class = SubtopicSerializer
    permission_classes = [AdminWriteOrReadOnly]

class FlashcardViewSet(viewsets.ModelViewSet):
    queryset = Flashcard.objects.all()
    serializer_class = FlashcardSerializer
    permission_classes = [AdminWriteOrReadOnly]

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [AdminWriteOrReadOnly]

# For Dashboard:

class UserDomainCoursesAPIView(viewsets.ReadOnlyModelViewSet):
    """
    Returns all domains with user's enrolled and unenrolled courses.
    """
    serializer_class = DomainWithCoursesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Domain.objects.all()

    def get_serializer_context(self):
        # pass the request to serializer for accessing request.user
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# For Course Details:

class CourseDetailAPIView(viewsets.ReadOnlyModelViewSet):
    """
    Returns detailed course information including announcements, chapters, and subtopics.
    """
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Course.objects.all()
    lookup_field = 'id'  # allows /course-details/<id>/

###

from payments.models import DomainSubscription


class PaidDomainsAPIView(viewsets.ReadOnlyModelViewSet):
    """
    Returns only paid domains for the authenticated user (where is_active=True)
    using the same structure as the dashboard.
    """
    serializer_class = DomainWithCoursesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        paid_domain_ids = DomainSubscription.objects.filter(
            user=user, is_active=True
        ).values_list('domain_id', flat=True)
        return Domain.objects.filter(id__in=paid_domain_ids)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UnpaidDomainsAPIView(viewsets.ReadOnlyModelViewSet):
    """
    Returns unpaid (non-subscribed) domains for the authenticated user
    using the same structure as the dashboard.
    """
    serializer_class = DomainWithCoursesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        paid_domain_ids = DomainSubscription.objects.filter(
            user=user, is_active=True
        ).values_list('domain_id', flat=True)
        return Domain.objects.exclude(id__in=paid_domain_ids)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

