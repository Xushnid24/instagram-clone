from django.urls import path
from . import views

app_name = 'posts'   # 👈 ВОТ ЭТО ГЛАВНОЕ

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('create/', views.post_create, name='post_create'),
    path('<int:pk>/', views.post_detail, name='post_detail'),  # 👈 если нет — добавь
    path('<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('like/<int:post_id>/', views.post_like, name='post_like'),
    path('<int:pk>/delete/', views.post_delete, name='post_delete'),
]
