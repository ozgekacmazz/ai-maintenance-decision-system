from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated

from apps.core.openapi import ProjectSchemaGenerator


class ProjeSchemaView(SpectacularAPIView):
    generator_class = ProjectSchemaGenerator
    permission_classes = (IsAuthenticated,)


class ProjeDocsView(SpectacularSwaggerView):
    permission_classes = (IsAuthenticated,)
