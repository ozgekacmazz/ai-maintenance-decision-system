from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class BakimSayfalama(PageNumberPagination):
    page_size = 20
    page_size_query_param = "sayfa_boyutu"
    max_page_size = 100
    page_query_param = "sayfa"

    def get_page_size(self, request):
        value = request.query_params.get(self.page_size_query_param)
        if value is None:
            return self.page_size
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                {"sayfa_boyutu": ["Geçerli bir tam sayı girin."]}
            ) from exc
        if value < 1 or value > self.max_page_size:
            raise ValidationError(
                {"sayfa_boyutu": ["Değer 1 ile 100 arasında olmalıdır."]}
            )
        return value

    def paginate_queryset(self, queryset, request, view=None):
        value = request.query_params.get(self.page_query_param)
        if value is not None:
            try:
                if int(value) < 1:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    {"sayfa": ["Geçerli bir pozitif tam sayı girin."]}
                ) from exc
        try:
            return super().paginate_queryset(queryset, request, view)
        except Exception as exc:
            from rest_framework.exceptions import NotFound

            if isinstance(exc, NotFound):
                raise ValidationError(
                    {"sayfa": ["İstenen sayfa mevcut değil."]}
                ) from exc
            raise
