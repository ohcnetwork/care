from django.utils.deprecation import MiddlewareMixin


class AddSlashMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path_info:
            if request.path_info[-1] != "/":
                request.path += "/"
                request.path_info += "/"
