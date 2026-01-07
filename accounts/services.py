"""
Сервисный слой для бизнес-логики друзей
Разделяем логику представлений и моделей
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.db.models import Q, Count
from .models import FriendRequest, Profile, Notification, BlockedUser


class FriendshipService:
    """Сервис для управления дружбой"""

    @staticmethod
    def send_friend_request(from_user, to_user_id, message=''):
        """
        Отправка запроса в друзья

        Args:
            from_user: Отправитель (User)
            to_user_id: ID получателя
            message: Опциональное сообщение

        Returns:
            FriendRequest: Созданный запрос

        Raises:
            ValidationError: При невалидных данных
        """
        try:
            to_user = User.objects.select_related('profile').get(id=to_user_id)
        except User.DoesNotExist:
            raise ValidationError("Пользователь не найден")

        # Проверки
        if from_user == to_user:
            raise ValidationError("Нельзя отправить запрос самому себе")

        # Проверка на блокировку
        if BlockedUser.objects.filter(blocker=to_user, blocked=from_user).exists():
            raise ValidationError("Этот пользователь заблокировал вас")

        if BlockedUser.objects.filter(blocker=from_user, blocked=to_user).exists():
            raise ValidationError("Вы заблокировали этого пользователя")

        # Проверка на существующую дружбу
        if from_user.profile.are_friends(to_user.profile):
            raise ValidationError("Вы уже друзья")

        # Проверка на существующий запрос
        existing_request = FriendRequest.objects.filter(
            from_user=from_user,
            to_user=to_user,
            status='pending'
        ).first()

        if existing_request:
            raise ValidationError("Запрос уже отправлен")

        # Проверка на обратный запрос
        reverse_request = FriendRequest.objects.filter(
            from_user=to_user,
            to_user=from_user,
            status='pending'
        ).first()

        if reverse_request:
            # Автоматически принимаем обратный запрос
            reverse_request.accept()
            return reverse_request

        # Создаём новый запрос
        with transaction.atomic():
            friend_request = FriendRequest.objects.create(
                from_user=from_user,
                to_user=to_user,
                message=message
            )

            # Создаём уведомление
            Notification.objects.create(
                user=to_user,
                notification_type='friend_request',
                related_user=from_user,
                message=f"{from_user.username} отправил вам запрос в друзья",
                link=f"/accounts/friend-requests/"
            )

        return friend_request

    @staticmethod
    def remove_friend(user, friend_user_id):
        """
        Удалить из друзей

        Args:
            user: Пользователь (User)
            friend_user_id: ID друга для удаления

        Raises:
            ValidationError: При невалидных данных
        """
        try:
            friend_user = User.objects.select_related('profile').get(id=friend_user_id)
        except User.DoesNotExist:
            raise ValidationError("Пользователь не найден")

        user_profile = user.profile
        friend_profile = friend_user.profile

        if not user_profile.are_friends(friend_profile):
            raise ValidationError("Вы не друзья")

        with transaction.atomic():
            # Удаляем из друзей (ManyToMany symmetrical=True удалит с обеих сторон)
            user_profile.friends.remove(friend_profile)

            # Удаляем все связанные запросы в друзья
            FriendRequest.objects.filter(
                Q(from_user=user, to_user=friend_user) |
                Q(from_user=friend_user, to_user=user)
            ).delete()

    @staticmethod
    def get_mutual_friends(user1, user2):
        """
        Получить общих друзей

        Args:
            user1: Первый пользователь (User)
            user2: Второй пользователь (User)

        Returns:
            QuerySet: Общие друзья
        """
        profile1_friends = set(user1.profile.friends.values_list('id', flat=True))
        profile2_friends = set(user2.profile.friends.values_list('id', flat=True))

        mutual_ids = profile1_friends.intersection(profile2_friends)

        return Profile.objects.filter(id__in=mutual_ids).select_related('user')

    @staticmethod
    def get_friend_suggestions(user, limit=10):
        """
        Получить рекомендации друзей (друзья друзей)

        Args:
            user: Пользователь (User)
            limit: Количество рекомендаций

        Returns:
            QuerySet: Рекомендованные пользователи
        """
        # Получаем ID друзей
        friend_ids = user.profile.friends.values_list('id', flat=True)

        # Получаем ID друзей друзей, исключая текущего пользователя и его друзей
        suggestions = Profile.objects.filter(
            friends__id__in=friend_ids
        ).exclude(
            id=user.profile.id
        ).exclude(
            id__in=friend_ids
        ).annotate(
            mutual_count=Count('friends', filter=Q(friends__id__in=friend_ids))
        ).order_by('-mutual_count')[:limit]

        return suggestions


class BlockingService:
    """Сервис для блокировки пользователей"""

    @staticmethod
    def block_user(blocker, blocked_user_id, reason=''):
        """
        Заблокировать пользователя

        Args:
            blocker: Блокирующий (User)
            blocked_user_id: ID блокируемого
            reason: Причина блокировки

        Returns:
            BlockedUser: Запись блокировки
        """
        try:
            blocked = User.objects.get(id=blocked_user_id)
        except User.DoesNotExist:
            raise ValidationError("Пользователь не найден")

        if blocker == blocked:
            raise ValidationError("Нельзя заблокировать себя")

        # Проверка на существующую блокировку
        existing = BlockedUser.objects.filter(
            blocker=blocker,
            blocked=blocked
        ).first()

        if existing:
            raise ValidationError("Пользователь уже заблокирован")

        with transaction.atomic():
            # Создаём блокировку
            block = BlockedUser.objects.create(
                blocker=blocker,
                blocked=blocked,
                reason=reason
            )

            # Удаляем из друзей если были друзьями
            blocker_profile = blocker.profile
            blocked_profile = blocked.profile

            if blocker_profile.are_friends(blocked_profile):
                blocker_profile.friends.remove(blocked_profile)

            # Удаляем все запросы в друзья
            FriendRequest.objects.filter(
                Q(from_user=blocker, to_user=blocked) |
                Q(from_user=blocked, to_user=blocker)
            ).delete()

        return block

    @staticmethod
    def unblock_user(blocker, blocked_user_id):
        """
        Разблокировать пользователя

        Args:
            blocker: Разблокирующий (User)
            blocked_user_id: ID разблокируемого
        """
        try:
            blocked = User.objects.get(id=blocked_user_id)
        except User.DoesNotExist:
            raise ValidationError("Пользователь не найден")

        block = BlockedUser.objects.filter(
            blocker=blocker,
            blocked=blocked
        ).first()

        if not block:
            raise ValidationError("Пользователь не заблокирован")

        block.delete()