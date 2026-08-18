from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import SaglikSerializer
from apps.core.services import saglik_durumunu_getir


class SaglikView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        saglik = saglik_durumunu_getir()
        serializer = SaglikSerializer(saglik)
        http_status = (
            status.HTTP_200_OK
            if saglik.veritabani == "bagli"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(serializer.data, status=http_status)
