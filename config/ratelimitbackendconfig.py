from ratelimitbackend.backends import RateLimitModelBackend

class MyBackend(RateLimitModelBackend):
    minutes = 20
    requests = 2

    def key(self, request, dt):
        return '%s%s-%s-%s' % (
            self.cache_prefix,
            self.get_ip(request),
            request.POST['username'],
            dt.strftime('%Y%m%d%H%M'),
        )
