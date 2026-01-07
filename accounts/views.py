from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError

from .forms import RegisterForm
from .models import FriendRequest, Profile, BlockedUser
from .services import FriendshipService


# ============ Authentication Views ============

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:login')  # или просто 'post_list' если нет namespace

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, 'Аккаунт успешно создан! Теперь войдите.')
                return redirect('accounts:login')  # ✅ С namespace
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile', user_id=request.user.id)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        # логин по email
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)

            # обновляем last_seen
            user.profile.last_seen = timezone.now()
            user.profile.save(update_fields=['last_seen'])

            messages.success(request, f'Добро пожаловать, {user.username}!')

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # ✅ ВАЖНО: редирект в профиль
            return redirect('accounts:profile', user_id=user.id)

        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')

    return render(request, 'accounts/login.html')



@login_required
def logout_view(request):
    """Выход пользователя"""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('accounts:login')  # <-- namespace accounts


# ============ Friend Request Views ============

@login_required
@require_POST
def send_friend_request(request, user_id):
    """Отправка запроса в друзья"""
    try:
        service = FriendshipService()
        friend_request = service.send_friend_request(request.user, user_id)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Запрос отправлен',
                'request_id': friend_request.id
            })

        messages.success(request, 'Запрос в друзья отправлен!')
        return redirect('accounts:profile', user_id=user_id)

    except ValidationError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('accounts:profile', user_id=user_id)


@login_required
def friend_requests_view(request):
    """Список входящих запросов"""
    incoming_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user', 'from_user__profile').order_by('-timestamp')

    outgoing_requests = FriendRequest.objects.filter(
        from_user=request.user,
        status='pending'
    ).select_related('to_user', 'to_user__profile').order_by('-timestamp')

    context = {
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
        'incoming_count': incoming_requests.count(),
    }

    return render(request, 'accounts/friend_requests.html', context)


@login_required
@require_POST
def accept_friend_request(request, request_id):
    """Принять запрос в друзья"""
    try:
        friend_request = get_object_or_404(
            FriendRequest,
            id=request_id,
            to_user=request.user,
            status='pending'
        )
        friend_request.accept()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Запрос принят'})

        messages.success(request, f'Вы теперь друзья с {friend_request.from_user.username}!')
        return redirect('accounts:friend_requests')

    except ValidationError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('accounts:friend_requests')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Произошла ошибка'}, status=500)
        messages.error(request, 'Произошла ошибка при обработке запроса')
        return redirect('accounts:friend_requests')


@login_required
@require_POST
def reject_friend_request(request, request_id):
    """Отклонить запрос"""
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )
    friend_request.reject()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Запрос отклонён'})

    messages.info(request, 'Запрос отклонён.')
    return redirect('accounts:friend_requests')


@login_required
@require_POST
def cancel_friend_request(request, request_id):
    """Отменить отправленный запрос"""
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        from_user=request.user,
        status='pending'
    )
    friend_request.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Запрос отменён'})

    messages.info(request, 'Запрос отменён.')
    return redirect('accounts:friend_requests')


@login_required
@require_POST
def remove_friend(request, user_id):
    """Удалить из друзей"""
    try:
        service = FriendshipService()
        service.remove_friend(request.user, user_id)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Удалено из друзей'})

        messages.success(request, 'Пользователь удалён из друзей.')
        return redirect('accounts:profile', user_id=user_id)

    except ValidationError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('accounts:profile', user_id=user_id)

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Произошла ошибка'}, status=500)
        messages.error(request, 'Ошибка при удалении из друзей')
        return redirect('accounts:profile', user_id=user_id)


# ============ User List & Search ============

class AllUsersView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/all_users.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id).select_related('profile')
        blocked_ids = BlockedUser.objects.filter(blocker=self.request.user).values_list('blocked_id', flat=True)
        queryset = queryset.exclude(id__in=blocked_ids)

        sort = self.request.GET.get('sort', 'username')
        if sort == 'username':
            queryset = queryset.order_by('username')
        elif sort == 'date_joined':
            queryset = queryset.order_by('-date_joined')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sort'] = self.request.GET.get('sort', 'username')
        return context


@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'users': [], 'message': 'Введите минимум 2 символа'})

    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related('profile')[:20]

    blocked_ids = BlockedUser.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    users = users.exclude(id__in=blocked_ids)

    data = []
    for user in users:
        is_friend = request.user.profile.are_friends(user.profile)
        request_sent = FriendRequest.objects.filter(from_user=request.user, to_user=user, status='pending').exists()

        data.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'avatar': user.profile.avatar.url if user.profile.avatar else None,
            'is_friend': is_friend,
            'request_sent': request_sent,
            'is_online': user.profile.is_online(),
        })

    return JsonResponse({'users': data})


# ============ Profile Views ============

class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    pk_url_kwarg = 'user_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object
        profile, _ = Profile.objects.get_or_create(user=profile_user)

        context['profile'] = profile
        context['is_self'] = (self.request.user == profile_user)
        context['is_friend'] = self.request.user.profile.are_friends(profile)
        context['request_sent'] = FriendRequest.objects.filter(from_user=self.request.user, to_user=profile_user, status='pending').exists()
        context['incoming_request'] = FriendRequest.objects.filter(from_user=profile_user, to_user=self.request.user, status='pending').first()
        context['is_blocked'] = BlockedUser.objects.filter(blocker=self.request.user, blocked=profile_user).exists()
        context['friends'] = profile.friends.select_related('user')[:12]
        if hasattr(profile_user, 'post_set'):
            context['posts'] = profile_user.post_set.all()[:9]

        return context


@login_required
def friends_list_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    friends = profile.friends.select_related('user').order_by('user__username')
    paginator = Paginator(friends, 24)
    page = request.GET.get('page', 1)
    friends_page = paginator.get_page(page)

    context = {
        'profile_user': user,
        'friends': friends_page,
        'is_self': (request.user == user)
    }

    return render(request, 'accounts/friends_list.html', context)


# ============ Notifications ============

@login_required
def notifications_view(request):
    notifications = request.user.notifications.select_related('related_user', 'related_user__profile').order_by('-created_at')[:50]
    request.user.notifications.filter(is_read=False).update(is_read=True)

    return render(request, 'accounts/notifications.html', {'notifications': notifications})


@login_required
def get_unread_notifications(request):
    notifications = request.user.notifications.filter(is_read=False).select_related('related_user')[:10]

    data = [{
        'id': n.id,
        'type': n.notification_type,
        'message': n.message,
        'created_at': n.created_at.isoformat(),
        'link': n.link,
        'user': {
            'username': n.related_user.username if n.related_user else None,
            'avatar': n.related_user.profile.avatar.url if n.related_user and n.related_user.profile.avatar else None
        }
    } for n in notifications]

    return JsonResponse({'notifications': data, 'count': request.user.notifications.filter(is_read=False).count()})


from django.contrib.auth.decorators import login_required
from .forms import ProfileEditForm


@login_required
def edit_profile_view(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST,
            request.FILES,
            instance=request.user.profile,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('accounts:profile', user_id=request.user.id)
    else:
        form = ProfileEditForm(
            instance=request.user.profile,
            user=request.user
        )

    return render(request, 'accounts/edit_profile.html', {'form': form})

def handler404(request, exception):
    """Кастомная страница 404"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Кастомная страница 500"""
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    """Кастомная страница 403"""
    return render(request, 'errors/403.html', status=403)

# Создаём экземпляры для urls.py
all_users = AllUsersView.as_view()
profile_view = ProfileView.as_view()
