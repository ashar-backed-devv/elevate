from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from content.views import DomainViewSet, CourseViewSet, AnnouncementViewSet, ChapterViewSet, SubtopicViewSet, FlashcardViewSet, QuestionViewSet, UserDomainCoursesAPIView, CourseDetailAPIView, PaidDomainsAPIView, UnpaidDomainsAPIView
from user_extras.views import FavoriteViewSet, NotificationViewSet, ChatMessageViewSet, AdminProcessPDFView, AdminDeleteNamespaceView, ChatbotQueryView

router = DefaultRouter()
# Content Routes (admin-only CRUD, authenticated read)
router.register(r'domains', DomainViewSet, basename='domain')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'subtopics', SubtopicViewSet, basename='subtopic')
router.register(r'flashcards', FlashcardViewSet, basename='flashcard')
router.register(r'questions', QuestionViewSet, basename='question')

# User Extras Routes (user-specific)
router.register(r'favorites', FavoriteViewSet, basename='favorite')  # Added basename
router.register(r'notifications', NotificationViewSet, basename='notification')  # Added basename
router.register(r'chat_messages', ChatMessageViewSet, basename='chat_message')  # Added basename

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    # 🟢 New: Add Djoser Social Auth URLs
    re_path(r'^auth/', include('djoser.social.urls')),
    path('', include(router.urls)),
    
    # Chatbot
    path('process_pdf/', AdminProcessPDFView.as_view(), name='process_pdf'),  # Added basename
    path('delete_namespace/', AdminDeleteNamespaceView.as_view(), name='delete_namespace'),  # Added basename
    path('query/', ChatbotQueryView.as_view(), name='query')  # Added basename
]
