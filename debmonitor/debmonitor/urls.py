"""DebMonitor URL Configuration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from debmonitor import views
from django.conf import settings

if settings.DEBMONITOR_CONFIG.get('CAS', {}):
    import django_cas_ng.views

urlpatterns = [
    path('', views.index, name='index'),
    path('search', views.search, name='search'),
    path('hosts/', include('hosts.urls')),
    path('images/', include('images.urls')),
    path('kernels/', include('kernels.urls')),
    path('packages/', include('bin_packages.urls')),
    path('source-packages/', include('src_packages.urls')),
    path('admin/', admin.site.urls),
]


if settings.DEBMONITOR_CONFIG.get('CAS', {}):
    urlpatterns.append(path('login/', django_cas_ng.views.LoginView.as_view(), name='login'))
    urlpatterns.append(path('logout/', django_cas_ng.views.LogoutView.as_view(), name='logout'))
else:
    urlpatterns.append(
        path('login/', auth_views.LoginView.as_view(
            template_name='login.html', extra_context={'title': 'Log in', 'subtitle': ''}), name='login'))
    urlpatterns.append(
        path('logout/', auth_views.LogoutView.as_view(), name='logout'))
