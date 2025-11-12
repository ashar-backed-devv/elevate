from django.contrib import admin
from .models import Favorite, Notification, ChatMessage

# Register your models here.
admin.site.register([Favorite, Notification, ChatMessage])