from django.urls import path

from hosts import views


app_name = 'hosts'
urlpatterns = [
    path('', views.index, name='index'),
    path('<name>', views.DetailView.as_view(), name='detail'),
    path('<name>/update', views.update, name='update'),
]
