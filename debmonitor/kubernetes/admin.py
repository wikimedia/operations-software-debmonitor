from django.contrib import admin
from kubernetes.models import KubernetesImage


admin.site.register(KubernetesImage)
