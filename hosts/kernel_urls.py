from django.urls import path
from hosts import views


app_name = 'kernels'
urlpatterns = [
    path('', views.kernel_index, name='index'),
    path('<slug:slug>', views.kernel_detail, name='detail'),
]
