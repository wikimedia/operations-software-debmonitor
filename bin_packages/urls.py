from django.urls import path

from bin_packages import views


app_name = 'bin_packages'
urlpatterns = [
    path('', views.index, name='index'),
    path('<name>', views.detail, name='detail'),
]
