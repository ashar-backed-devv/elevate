from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from notes.views import NoteViewSet
from events.views import EventViewSet  # ⬅️ Import EventViewSet
from payments.views import (
    FreeTierActivateView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    CancelSubscriptionView,
    SubscriptionStatusView,
    FreeTierStatusView,
    #CreateMultipleSubscriptionsCheckoutSessionView,
    UserDomainSubscriptionViewSet
)
from content.views import DomainViewSet, CourseViewSet, AnnouncementViewSet, ChapterViewSet, SubtopicViewSet, FlashcardViewSet, QuestionViewSet, UserDomainCoursesAPIView, CourseDetailAPIView, PaidDomainsAPIView, UnpaidDomainsAPIView
from user_extras.views import FavoriteViewSet, NotificationViewSet, ChatMessageViewSet, AdminProcessPDFView, AdminDeleteNamespaceView, ChatbotQueryView
from user_progress.views import UserCourseViewSet, QuizCourseProgressViewSet, TestCourseProgressViewSet
from platform_specifics.views import HelpCenterViewSet, BlogViewSet, BlogReplyViewSet, NewsletterSubscriptionViewSet, GeneralAnnouncementViewSet, HeroSectionViewSet

router = DefaultRouter()
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'events', EventViewSet, basename='event')  # ⬅️ Register EventViewSet

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

# Progress Routes (user-specific)
router.register(r'user_courses', UserCourseViewSet, basename='user_course')  # Added basename
router.register(r'quiz_progress', QuizCourseProgressViewSet, basename='quiz_progress')
router.register(r'test_progress', TestCourseProgressViewSet, basename='test_progress')

# Platform Routes (public access)
router.register(r'help_center', HelpCenterViewSet, basename='help_center')
router.register(r'blogs', BlogViewSet, basename='blog')
router.register(r'blog_replies', BlogReplyViewSet, basename='blog_reply')
router.register(r'newsletter_subscriptions', NewsletterSubscriptionViewSet, basename='newsletter_subscription')
router.register(r'general_announcements', GeneralAnnouncementViewSet, basename='general_announcement')
router.register(r'hero_sections', HeroSectionViewSet, basename='hero_section')

# Dashboard Routes (user-specific)
router.register(r'dashboard', UserDomainCoursesAPIView, basename='dashboard' )
router.register(r'dashboard-paid', PaidDomainsAPIView, basename='dashboard-paid')
router.register(r'dashboard-unpaid', UnpaidDomainsAPIView, basename='dashboard-unpaid')

# Course Detail Routes (public)
router.register(r'course_details', CourseDetailAPIView, basename='course_details')

# User All Active Domains
router.register(r'user_active_domains', UserDomainSubscriptionViewSet, basename='user_active_domains')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    # 🟢 New: Add Djoser Social Auth URLs
    re_path(r'^auth/', include('djoser.social.urls')),
    path('', include(router.urls)),

    # 🟣 Payment Routes
    path('api/free-tier/status/', FreeTierStatusView.as_view(), name='free-tier-status'),  # 👈 new endpoint
    path('api/free-tier/activate/', FreeTierActivateView.as_view(), name='free-tier-activate'),
    path('api/stripe/create-checkout-session/', CreateCheckoutSessionView.as_view(), name='stripe-checkout-session'),
    path('api/stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('api/subscription/<int:domain_id>/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('api/subscription/<int:domain_id>/status/', SubscriptionStatusView.as_view(), name='subscription-status'),

    # Chatbot
    path('process_pdf/', AdminProcessPDFView.as_view(), name='process_pdf'),  # Added basename
    path('delete_namespace/', AdminDeleteNamespaceView.as_view(), name='delete_namespace'),  # Added basename
    path('query/', ChatbotQueryView.as_view(), name='query')  # Added basename
]