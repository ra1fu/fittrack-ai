from rest_framework import serializers


class EmptyMetaSerializer(serializers.Serializer):
    pass


class HealthDataSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class HealthResponseSerializer(serializers.Serializer):
    data = HealthDataSerializer()
    meta = EmptyMetaSerializer()
