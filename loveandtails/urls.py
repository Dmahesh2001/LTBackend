from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_v1 = [
    path('', include('apps.core.urls')),
    path('', include('apps.users.urls')),
    path('', include('apps.waitlist.urls')),
]

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='swagger-ui'), name='root'),
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/v1/', include(api_v1)),
    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
