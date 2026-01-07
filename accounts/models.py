from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_private = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'profiles'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-created_at']

    def __str__(self):
        return f"Профиль {self.user.username}"

    def is_online(self):
        """Проверка активности пользователя (онлайн последние 5 минут)"""
        return timezone.now() - self.last_seen < timezone.timedelta(minutes=5)

    def get_friends_count(self):
        return self.friends.count()

    def are_friends(self, other_profile):
        """Проверка дружбы с другим профилем"""
        return self.friends.filter(id=other_profile.id).exists()


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Автоматическое создание/обновление профиля"""
    if created:
        Profile.objects.create(user=instance)
    else:
        # Обновляем профиль если он существует
        Profile.objects.get_or_create(user=instance)


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принята'),
        ('rejected', 'Отклонена'),
    ]

    from_user = models.ForeignKey(
        User,
        related_name='sent_friend_requests',
        on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        User,
        related_name='received_friend_requests',
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    message = models.TextField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'friend_requests'
        verbose_name = 'Запрос в друзья'
        verbose_name_plural = 'Запросы в друзья'
        ordering = ['-timestamp']
        unique_together = ('from_user', 'to_user')
        indexes = [
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['from_user', 'status']),
        ]

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.get_status_display()})"

    def clean(self):
        """Валидация перед сохранением"""
        if self.from_user == self.to_user:
            raise ValidationError("Нельзя отправить запрос самому себе")

        # Проверка на существующую дружбу
        from_profile = self.from_user.profile
        to_profile = self.to_user.profile
        if from_profile.are_friends(to_profile):
            raise ValidationError("Вы уже друзья")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def accept(self):
        """Принять запрос в друзья"""
        if self.status != 'pending':
            raise ValidationError("Запрос уже обработан")

        self.status = 'accepted'
        self.save()

        # Добавляем в друзья
        from_profile = self.from_user.profile
        to_profile = self.to_user.profile

        from_profile.friends.add(to_profile)
        to_profile.friends.add(from_profile)

        # Создаём уведомление
        Notification.objects.create(
            user=self.from_user,
            notification_type='friend_accepted',
            related_user=self.to_user,
            message=f"{self.to_user.username} принял ваш запрос в друзья"
        )

    def reject(self):
        """Отклонить запрос"""
        if self.status != 'pending':
            raise ValidationError("Запрос уже обработан")

        self.status = 'rejected'
        self.save()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('friend_request', 'Запрос в друзья'),
        ('friend_accepted', 'Запрос принят'),
        ('post_like', 'Лайк на пост'),
        ('comment', 'Комментарий'),
        ('mention', 'Упоминание'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    related_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='triggered_notifications',
        null=True,
        blank=True
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.get_notification_type_display()}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


class BlockedUser(models.Model):
    """Модель для блокировки пользователей"""
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking'
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'blocked_users'
        unique_together = ('blocker', 'blocked')
        verbose_name = 'Заблокированный пользователь'
        verbose_name_plural = 'Заблокированные пользователи'

    def __str__(self):
        return f"{self.blocker.username} заблокировал {self.blocked.username}"