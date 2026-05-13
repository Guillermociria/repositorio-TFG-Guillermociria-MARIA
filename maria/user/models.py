from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    telefono = models.CharField(max_length=15, blank=True, null=True)
    openai_api_key = models.CharField(max_length=255, blank=True, null=True)
    anthropic_api_key = models.CharField(max_length=255, blank=True, null=True)
    google_api_key = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username