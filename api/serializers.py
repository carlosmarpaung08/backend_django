from rest_framework import serializers
from .models import CustomUser
from .models import UserBookRecommendation

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'bio', 'profile_picture')

    def create(self, validated_data):
        # Pastikan password dienkripsi sebelum disimpan
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
class UserBookRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBookRecommendation
        fields = '__all__'