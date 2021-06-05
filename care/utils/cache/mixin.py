from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

cache_limit = settings.API_CACHE_DURATION_IN_SECONDS


class BaseCacheResponseMixin:
    pass


class ListCacheResponseMixin(BaseCacheResponseMixin):

    @method_decorator(cache_page(cache_limit))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RetrieveCacheResponseMixin(BaseCacheResponseMixin):

    @method_decorator(cache_page(cache_limit))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CacheResponseMixin(RetrieveCacheResponseMixin, ListCacheResponseMixin):
    pass
