from .models import FriendRequest

def friend_requests_count(request):
    if request.user.is_authenticated:
        count = FriendRequest.objects.filter(to_user=request.user, status='pending').count()
    else:
        count = 0
    return {'incoming_count': count}
