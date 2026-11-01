# ==============================================================================
# Paginación Estándar de la API - MPDW
# SAD Ref: §9.1
# ==============================================================================
from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Paginación con parámetros page y size (20, 50, 100)."""

    page_query_param = "page"
    page_size_query_param = "size"
    page_size = 20
    max_page_size = 100

    def get_paginated_response(self, data: list) -> Response:
        assert self.page is not None
        assert self.request is not None
        return Response(
            OrderedDict(
                [
                    ("total", self.page.paginator.count),
                    ("page", self.page.number),
                    ("size", self.get_page_size(self.request)),
                    ("results", data),
                ]
            )
        )

