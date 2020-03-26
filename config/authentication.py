from rest_framework.authentication import BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate_header(self, request):
        return ""


class CustomBasicAuthentication(BasicAuthentication):
    def authenticate_header(self, request):
        return ""
