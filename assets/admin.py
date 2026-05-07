from django.contrib import admin

from assets.models import Asset, Category, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("name", "sn", "status", "department")
    search_fields = ("name", "sn")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
