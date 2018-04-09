"""DebMonitor URL Configuration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from debmonitor import views


urlpatterns = [
    path('', views.index, name='index'),
    path('hosts/', include('hosts.urls')),
    path('kernels/', include('hosts.kernel_urls')),
    path('packages/', include('bin_packages.urls')),
    path('source-packages/', include('src_packages.urls')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html', extra_context={'title': 'Log in', 'subtitle': ''}), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
