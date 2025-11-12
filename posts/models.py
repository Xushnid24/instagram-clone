from django.db import models
from django.utils import timezone


class Post(models.Model):
    title = models.CharField(max_length=200, default="Без заголовка")
    content = models.TextField(default="Пост пока пустой")
    created_at = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return self.title


