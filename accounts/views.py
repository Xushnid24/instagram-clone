from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import RegisterForm, ProfileEditForm
from .models import FriendRequest, Profile
from django.http import JsonResponse
from posts.models import Post

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('post_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)


    if request.user == to_user:
        return redirect('profile', user_id=to_user.id)


    FriendRequest.objects.get_or_create(
        from_user=request.user,
        to_user=to_user,
        accepted=False,
        rejected=False
    )

    return redirect('profile', user_id=to_user.id)


@login_required
def friend_requests(request):
    requests = FriendRequest.objects.filter(
        to_user=request.user,
        accepted=False,
        rejected=False
    )
    return render(request, 'accounts/friend_requests.html', {'requests': requests})


@login_required
def accept_friend_request(request, request_id):
    f_request = get_object_or_404(FriendRequest, id=request_id)


    if f_request.to_user != request.user:
        return redirect('friend_requests')

    profile1 = request.user.profile
    profile2 = f_request.from_user.profile

    profile1.friends.add(profile2)
    profile2.friends.add(profile1)

    f_request.accepted = True
    f_request.save()

    return redirect('friend_requests')


@login_required
def reject_friend_request(request, request_id):
    f_request = get_object_or_404(FriendRequest, id=request_id)
    if f_request.to_user == request.user:
        f_request.rejected = True
        f_request.save()
    return redirect('friend_requests')


@login_required
def all_users(request):
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'accounts/all_users.html', {'users': users})



@login_required
def profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    profile = profile_user.profile

    is_self = request.user == profile_user
    is_friend = profile.friends.filter(user=request.user).exists()

    request_sent = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=profile_user,
        accepted=False,
        rejected=False
    ).exists()

    incoming_request = FriendRequest.objects.filter(
        from_user=profile_user,
        to_user=request.user,
        accepted=False,
        rejected=False
    ).first()

    posts = Post.objects.filter(author=profile_user).order_by('-created_at')

    return render(request, 'accounts/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'is_self': is_self,
        'is_friend': is_friend,
        'request_sent': request_sent,
        'incoming_request': incoming_request,
        'posts': posts
    })


@login_required
def search_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(username__istartswith=query).exclude(id=request.user.id)

    data = []
    for u in users:
        data.append({
            'id': u.id,
            'username': u.username
        })

    return JsonResponse(data, safe=False)

@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', user_id=request.user.id)
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, 'accounts/edit_profile.html', {'form': form})

