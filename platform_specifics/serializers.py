# platform/serializers.py
from rest_framework import serializers
from .models import HelpCenter, Blog, BlogReply, NewsletterSubscription, GeneralAnnouncement, HeroSection

class HelpCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpCenter
        fields = ['id', 'name', 'email', 'subject', 'message', 'topic', 'created_at']

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['id', 'title', 'primary_description', 'secondary_description', 'author', 'date', 
                  'quotation', 'primary_sub_description', 'secondary_sub_description', 'created_at', 'updated_at']

class BlogReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogReply
        fields = ['id', 'blog', 'email', 'name', 'comment', 'created_at']

class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscription
        fields = ['id', 'email', 'created_at']

class GeneralAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralAnnouncement
        fields = ['id', 'title', 'description', 'datetime', 'status', 'created_at', 'updated_at']

class HeroSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSection
        fields = ['id', 'video_url', 'created_at', 'updated_at']

class BlogListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['id', 'title', 'primary_description']
