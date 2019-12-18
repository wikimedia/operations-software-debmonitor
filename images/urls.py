from django.urls import path

from images import views


app_name = 'images'
urlpatterns = [
    path('', views.index, name='index'),
    path('<path:name>/update', views.update_image, name='update'),
    path('<path:name>', views.DetailView.as_view(), name='detail'),
]
