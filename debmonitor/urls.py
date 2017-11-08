"""DebMonitor URL Configuration."""
from django.contrib import admin
from django.urls import include, path

from debmonitor import views


urlpatterns = [
    path('', views.index, name='index'),
    path('hosts/', include('hosts.urls')),
    path('kernels/', include('hosts.kernel_urls')),
    path('packages/', include('bin_packages.urls')),
    path('source-packages/', include('src_packages.urls')),
    path('admin/', admin.site.urls),
]
