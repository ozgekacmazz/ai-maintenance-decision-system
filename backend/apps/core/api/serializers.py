from rest_framework import serializers


class SaglikSerializer(serializers.Serializer):
    durum = serializers.CharField()
    servis = serializers.CharField()
    veritabani = serializers.CharField()
    migrationlar = serializers.CharField()
    model_dosyalari = serializers.CharField()
