from django.db import models
from django.utils import timezone

class Post(models.Model):
    title = models.CharField(max_length=200, default="Без заголовка")
    content = models.TextField(default="Пост пока пустой")
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    likes = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=100, default="Аноним")
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.author}: {self.text[:20]}'

