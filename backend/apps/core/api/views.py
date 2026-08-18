from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import SaglikSerializer
from apps.core.exceptions import HizmetKullanilamiyorHatasi
from apps.core.services import saglik_durumunu_getir


class SaglikView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        saglik = saglik_durumunu_getir()
        serializer = SaglikSerializer(saglik)
        if saglik.veritabani != "bagli":
            raise HizmetKullanilamiyorHatasi
        return Response(serializer.data, status=status.HTTP_200_OK)
