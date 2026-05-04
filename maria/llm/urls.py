from django.urls import path
from . import views

urlpatterns = [
    path('sprint/', views.sprint_view, name='generar_sprint'),
]