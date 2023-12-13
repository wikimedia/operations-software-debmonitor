from django.contrib import admin
from src_packages.models import OS, SrcPackage, SrcPackageVersion


admin.site.register(OS)
admin.site.register(SrcPackage)
admin.site.register(SrcPackageVersion)
