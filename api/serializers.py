from rest_framework import serializers
from .models import CustomUser, ReadingHistory

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

class ReadingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingHistory
        fields = '__all__'
