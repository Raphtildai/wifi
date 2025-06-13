# accounts/serializers.py
from rest_framework import serializers
from .models import User, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'user_type',
            'first_name',
            'last_name',
            'phone',
            'address',
            'credit',
            'is_verified',
            'stripe_customer_id',
            'profile',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        user = User.objects.create_user(**validated_data)
        # Create profile only if user is reseller and profile data exists
        if profile_data and user.user_type == 2:
            UserProfile.objects.create(user=user, **profile_data)
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile = getattr(instance, 'profile', None)
            if profile is None:
                profile = UserProfile.objects.create(user=instance, **profile_data)
            else:
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

        return instance