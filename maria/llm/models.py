import uuid
from django.conf import settings
from django.db import models

STAGE_CHOICES = [
    ('empatizar',  'Empatizar'),
    ('definir',    'Definir'),
    ('idear',      'Idear'),
    ('prototipar', 'Prototipar'),
    ('testear',    'Testear'),
]


class SprintSession(models.Model):
    STATUS_CHOICES = [('active', 'Activa'), ('completed', 'Completada')]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sprint_sessions')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    stages      = models.JSONField(default=list, blank=True)
    thread_id   = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Technique(models.Model):
    tech_id             = models.SlugField(max_length=50, unique=True)
    name                = models.CharField(max_length=100)
    icon                = models.CharField(max_length=10, default='⚙️')
    stage               = models.CharField(max_length=20, choices=STAGE_CHOICES, blank=True, default='')
    is_builtin          = models.BooleanField(default=False)
    inputs_description  = models.CharField(max_length=300, blank=True)
    outputs_description = models.CharField(max_length=300, blank=True)
    default_prompt      = models.TextField(blank=True, default='')
    questionnaire       = models.JSONField(default=list, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"
