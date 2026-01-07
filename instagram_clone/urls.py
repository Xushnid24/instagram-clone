from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('posts.urls')),
    path('accounts/', include('accounts.urls', namespace='accounts')),  # добавлен namespace
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'accounts.views.handler404'
handler500 = 'accounts.views.handler500'
handler403 = 'accounts.views.handler403'
