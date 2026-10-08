from django.urls import path
from .views import (ProjectListCreateView, ProjectDetailView, TaskListCreateView,
                    TaskDetailView, ExportView, MemberAddView, CommentListCreateView)

urlpatterns = [
    path('projects', ProjectListCreateView.as_view()),
    path('projects/<uuid:project_id>', ProjectDetailView.as_view()),
    path('projects/<uuid:project_id>/tasks', TaskListCreateView.as_view()),
    path('projects/<uuid:project_id>/members', MemberAddView.as_view()),
    path('projects/<uuid:project_id>/export', ExportView.as_view()),
    path('tasks/<uuid:task_id>', TaskDetailView.as_view()),
    path('tasks/<uuid:task_id>/comments', CommentListCreateView.as_view()),
]
