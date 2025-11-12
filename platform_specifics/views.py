from rest_framework import viewsets
from .models import HelpCenter, Blog, BlogReply, NewsletterSubscription, GeneralAnnouncement, HeroSection
from .serializers import (HelpCenterSerializer, BlogSerializer, BlogReplySerializer, 
                         NewsletterSubscriptionSerializer, GeneralAnnouncementSerializer, HeroSectionSerializer, BlogListSerializer)
from .permissions import AllowReadOrAdminWrite, AllowCreateOrAdminWrite
from rest_framework.decorators import action
from rest_framework.response import Response

class HelpCenterViewSet(viewsets.ModelViewSet):
    queryset = HelpCenter.objects.all()
    serializer_class = HelpCenterSerializer
    permission_classes = [AllowCreateOrAdminWrite]  # Authenticated read, public create, admin update/delete

class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by('-created_at')  # ✅ latest first
    serializer_class = BlogSerializer
    permission_classes = [AllowReadOrAdminWrite]  # Public read, admin CRUD

    def list(self, request, *args, **kwargs):
        """
        Returns all blogs in descending order by created_at.
        Only includes id, title, and primary_description.
        """
        blogs = self.get_queryset()
        serializer = BlogListSerializer(blogs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Returns only the 3 most recent blogs (id, title, primary_description).
        Example: /blogs/latest/
        """
        latest_blogs = Blog.objects.all().order_by('-created_at')[:3]
        serializer = BlogListSerializer(latest_blogs, many=True)
        return Response(serializer.data)


class BlogReplyViewSet(viewsets.ModelViewSet):
    queryset = BlogReply.objects.all()
    serializer_class = BlogReplySerializer
    permission_classes = [AllowCreateOrAdminWrite]  # Authenticated read, public create, admin update/delete --- public read and create

class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSubscriptionSerializer
    permission_classes = [AllowCreateOrAdminWrite]  # Authenticated read, public create, admin update/delete

class GeneralAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = GeneralAnnouncement.objects.all()
    serializer_class = GeneralAnnouncementSerializer
    permission_classes = [AllowReadOrAdminWrite]  # Public read, admin CRUD

class HeroSectionViewSet(viewsets.ModelViewSet):
    queryset = HeroSection.objects.all()
    serializer_class = HeroSectionSerializer
    permission_classes = [AllowReadOrAdminWrite]  # Public read, admin CRUD