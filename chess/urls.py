from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from .views import api, random_favicon


urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('AUTH.urls')),
    path('api/', api.as_view(), name='api'),
    path('', include('game.urls')),
    path('favicon.ico', random_favicon, name='favicon'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
