from rest_framework import serializers


class AuthenticationSerializer(serializers.Serializer):
    FirstName = serializers.CharField(
        max_length=100,
    )
    LastName = serializers.CharField(max_length=100)
    Email = serializers.EmailField()
    TokenId = serializers.CharField()
    ExpireTime = serializers.DateTimeField()
