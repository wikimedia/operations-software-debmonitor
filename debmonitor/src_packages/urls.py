from django.urls import path

from src_packages import views


app_name = 'src_packages'
urlpatterns = [
    path('', views.index, name='index'),
    path('<name>', views.detail, name='detail'),
]
