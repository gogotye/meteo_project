from rest_framework import serializers


class CityStatSerializer(serializers.Serializer):
    city = serializers.CharField()
    count = serializers.IntegerField()