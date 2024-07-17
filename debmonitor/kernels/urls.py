from django.urls import path

from kernels import views


app_name = 'kernels'
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:os_id>_<slug:slug>', views.detail, name='detail'),
]
