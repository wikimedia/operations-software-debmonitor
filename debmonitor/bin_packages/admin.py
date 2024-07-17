from django.contrib import admin
from bin_packages.models import Package, PackageVersion


admin.site.register(Package)
admin.site.register(PackageVersion)
