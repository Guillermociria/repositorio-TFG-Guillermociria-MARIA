from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
     path("feature-form/", views.feature_form_view, name="feature_form"),
]