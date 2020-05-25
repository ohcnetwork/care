from __future__ import unicode_literals

from rest_framework.pagination import LimitOffsetPagination


class CustomPagination(LimitOffsetPagination):
    """
    Custom pagination class used for pagination on list page
    """

    default_limit = 1
    page_size_query_param = "page_size"
    max_limit = 500
