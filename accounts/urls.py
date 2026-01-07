from django.urls import path
from .views import (
    # Authentication
    register_view,
    login_view,
    logout_view,

    # Friend Requests
    send_friend_request,
    friend_requests_view,
    accept_friend_request,
    reject_friend_request,
    cancel_friend_request,
    remove_friend,

    # Users & Profile
    all_users,
    search_users,
    profile_view,
    friends_list_view,
    edit_profile_view,  # <-- ДОБАВЬТЕ ЭТОТ ИМПОРТ!

    # Notifications
    notifications_view,
    get_unread_notifications,
)

app_name = 'accounts'

urlpatterns = [
    # ============ Authentication ============
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # ============ Friend Requests ============
    path('send-request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friend-requests/', friend_requests_view, name='friend_requests'),
    path('accept-request/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('reject-request/<int:request_id>/', reject_friend_request, name='reject_friend_request'),
    path('cancel-request/<int:request_id>/', cancel_friend_request, name='cancel_friend_request'),
    path('remove-friend/<int:user_id>/', remove_friend, name='remove_friend'),

    # ============ Users & Profiles ============
    path('users/', all_users, name='all_users'),
    path('search-users/', search_users, name='search_users'),
    path('profile/<int:user_id>/', profile_view, name='profile'),
    path('profile/<int:user_id>/friends/', friends_list_view, name='friends_list'),
    path('edit-profile/', edit_profile_view, name='edit_profile'),  # <-- ПЕРЕМЕСТИТЕ В ЭТОТ РАЗДЕЛ!

    # ============ Notifications ============
    path('notifications/', notifications_view, name='notifications'),
    path('api/notifications/unread/', get_unread_notifications, name='get_unread_notifications'),
]