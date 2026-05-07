from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Category, Department, Asset


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "parent"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            "id", "name", "sn", "price", "purchase_date",
            "status", "category", "department", "owner",
        ]

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.category:
            response['category'] = CategorySerializer(instance.category).data
        if instance.department:
            response['department'] = DepartmentSerializer(instance.department).data
        if instance.owner:
            response['owner'] = UserSerializer(instance.owner).data
        return response