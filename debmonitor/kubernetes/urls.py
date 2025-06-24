from django.urls import path

from kubernetes import views


app_name = 'kubernetes'
urlpatterns = [
    path('', views.index, name='index'),
]
