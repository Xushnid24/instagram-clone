from django.urls import path
from .views import (
    register_view, login_view, logout_view,
    send_friend_request, friend_requests,
    accept_friend_request, reject_friend_request,
    all_users, profile_view, search_users
)


urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('send-request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friend-requests/', friend_requests, name='friend_requests'),
    path('accept-request/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('reject-request/<int:request_id>/', reject_friend_request, name='reject_friend_request'),
    path('users/', all_users, name='all_users'),
    path('profile/<int:user_id>/', profile_view, name='profile'),
    path('search-users/', search_users, name='search_users'),



]
