from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from .views import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include('AUTH.urls')),
    path('api/', api.as_view()),
    path('', include('game.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
