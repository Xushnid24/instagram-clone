from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Profile
import re
from PIL import Image


class RegisterForm(forms.ModelForm):
    """Форма регистрации с расширенной валидацией"""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя',
            'autofocus': True
        }),
        help_text='От 3 до 150 символов. Только буквы, цифры и @/./+/-/_'
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        }),
        help_text='Обязательное поле'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        }),
        help_text='Минимум 8 символов'
    )

    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя (необязательно)'
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия (необязательно)'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if len(username) < 3:
            raise ValidationError('Имя пользователя должно содержать минимум 3 символа')

        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError('Используйте только буквы, цифры и символы @/./+/-/_')

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Это имя пользователя уже занято')

        forbidden_names = ['admin', 'root', 'system', 'moderator', 'administrator']
        if username.lower() in forbidden_names:
            raise ValidationError('Это имя пользователя зарезервировано')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')

        return email.lower()

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')

        if not any(char.isdigit() for char in password):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')

        if not any(char.isalpha() for char in password):
            raise ValidationError('Пароль должен содержать хотя бы одну букву')

        common_passwords = ['password', '12345678', 'qwerty123', 'admin123']
        if password.lower() in common_passwords:
            raise ValidationError('Этот пароль слишком простой')

        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()
            Profile.objects.get_or_create(user=user)

        return user


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя или Email',
            'autofocus': True
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class ProfileEditForm(forms.ModelForm):
    """Форма редактирования профиля"""

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'})
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'})
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )

    bio = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Расскажите о себе...',
            'rows': 4
        })
    )

    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Город, страна'})
    )

    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'})
    )

    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    is_private = forms.BooleanField(
        required=False,
        label='Приватный профиль',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Profile
        fields = ['bio', 'location', 'website', 'birth_date', 'avatar', 'is_private']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if self.user:
            if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
                raise ValidationError('Этот email уже используется')

        return email.lower()

    def clean_avatar(self):
        """ИСПРАВЛЕНО: корректная проверка изображения"""
        avatar = self.cleaned_data.get('avatar')

        if not avatar:
            return avatar

        if avatar.size > 5 * 1024 * 1024:
            raise ValidationError('Размер изображения не должен превышать 5MB')

        try:
            img = Image.open(avatar)
            img.verify()
        except Exception:
            raise ValidationError('Загрузите корректное изображение')

        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.email = self.cleaned_data.get('email', '')

            if commit:
                self.user.save()

        if commit:
            profile.save()

        return profile


class FriendRequestForm(forms.Form):
    message = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Добавить сообщение (необязательно)',
            'rows': 3
        })
    )
