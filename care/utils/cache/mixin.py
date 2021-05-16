from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class BaseCacheResponseMixin:
    pass


class ListCacheResponseMixin(BaseCacheResponseMixin):
    @method_decorator(cache_page(60 * 100))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RetrieveCacheResponseMixin(BaseCacheResponseMixin):
    @method_decorator(cache_page(60 * 100))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CacheResponseMixin(RetrieveCacheResponseMixin, ListCacheResponseMixin):
    pass
