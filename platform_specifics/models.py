# platform/models.py
from django.db import models

class HelpCenter(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    topic = models.CharField(max_length=100)  # e.g., "Technical Support", "Billing"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} by {self.name}"

class Blog(models.Model):
    title = models.CharField(max_length=255)
    primary_description = models.TextField()
    secondary_description = models.TextField(blank=True)
    author = models.CharField(max_length=255)
    date = models.DateTimeField()
    quotation = models.TextField(blank=True)
    primary_sub_description = models.TextField(blank=True)
    secondary_sub_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class BlogReply(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='replies')
    email = models.EmailField()
    name = models.CharField(max_length=255)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.name} on {self.blog.title}"

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class GeneralAnnouncement(models.Model):
    STATUS_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('urgent', 'Urgent'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class HeroSection(models.Model):
    video_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.video_url