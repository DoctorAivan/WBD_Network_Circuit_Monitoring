# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from api.models import ServerLog, Circuit, Group

# Sign Up Serializer
class SignUpSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()

# Sign In Serializer
class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

# Sign Response Serializer
class SignResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    token = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password"]

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "description", "color"]


class CircuitSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)

    class Meta:
        model = Circuit
        fields = ["id", "target_host", "range_up", "range_down", "group", "description"]

class CircuitViewSetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Circuit
        fields = ["id", "target_host", "range_up", "range_down", "group", "description"]

class ServerLogSerializer(serializers.ModelSerializer):
    circuit = CircuitSerializer(read_only=True)

    class Meta:
        model = ServerLog
        fields = [
            "id",
            "timestamp",
            "source_host",
            "circuit",
            "min_value",
            "avg_value",
            "max_value",
            "stddev_value",
        ]

class ServerLogChartSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ServerLog
        fields = [
            "id",
            "min_value",
            "avg_value",
            "max_value",
            "stddev_value",
            "timestamp"
        ]