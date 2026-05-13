from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('sprint/<int:session_id>/', views.sprint_view, name='sprint_session'),
    path('sprint/techniques/', views.technique_list, name='technique_list'),
    path('sprint/techniques/create/', views.technique_create, name='technique_create'),
    path('sprint/techniques/<slug:tech_id>/delete/', views.technique_delete, name='technique_delete'),
    path('sprint/techniques/<slug:tech_id>/simulate/', views.technique_simulate, name='technique_simulate'),
    path('sprint/<int:session_id>/export/', views.export_session, name='export_session'),
    path('sprint/<int:session_id>/delete/', views.delete_session, name='delete_session'),
]
