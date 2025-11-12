from django.contrib import admin
from .models import HelpCenter, Blog, BlogReply, NewsletterSubscription, GeneralAnnouncement, HeroSection

# Register your models here.
admin.site.register([HelpCenter, Blog, BlogReply, NewsletterSubscription, GeneralAnnouncement, HeroSection])