import json

import requests
from django.conf import settings
from django.core.cache import cache

GATEWAY_API_URL = "https://dev.abdm.gov.in/"
HEALTH_SERVICE_API_URL = "https://healthidsbx.abdm.gov.in/api"
ABDM_TOKEN_URL = GATEWAY_API_URL + "gateway/v0.5/sessions"
ABDM_TOKEN_CACHE_KEY = "abdm_token"


class APIGateway:
    def __init__(self, gateway, token):
        if gateway == "health":
            self.url = HEALTH_SERVICE_API_URL
        else:
            self.url = GATEWAY_API_URL
        self.token = token

    def encrypt(self, data):
        cert = cache.get("abdm_cert")
        if not cert:
            cert = requests.get(settings.ABDM_CERT_URL).text
            cache.set("abdm_cert", cert, 3600)

    def add_auth_header(self, headers):
        token = cache.get(ABDM_TOKEN_CACHE_KEY)
        print("Cached Token: {}".format(token))
        if not token:
            data = {
                "clientId": settings.ABDM_CLIENT_ID,
                "clientSecret": settings.ABDM_CLIENT_SECRET,
            }
            auth_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            resp = requests.post(
                ABDM_TOKEN_URL, data=json.dumps(data), headers=auth_headers
            )
            print("Token Response Status: {}".format(resp.status_code))
            if resp.status_code < 300:
                # Checking if Content-Type is application/json
                if resp.headers["Content-Type"] != "application/json":
                    print(
                        "Unsupported Content-Type: {}".format(
                            resp.headers["Content-Type"]
                        )
                    )
                    print("Response: {}".format(resp.text))
                    return None
                else:
                    data = resp.json()
                    token = data["accessToken"]
                    expires_in = data["expiresIn"]
                    print("New Token: {}".format(token))
                    print("Expires in: {}".format(expires_in))
                    cache.set(ABDM_TOKEN_CACHE_KEY, token, expires_in)
            else:
                print("Bad Response: {}".format(resp.text))
                return None
        print("Returning Authorization Header: Bearer {}".format(token))
        auth_header = {"Authorization": "Bearer {}".format(token)}
        return {**headers, **auth_header}

    def get(self, path, params=None):
        url = self.url + path
        headers = {}
        headers = self.add_auth_header(headers)
        response = requests.get(url, headers=headers, params=params)
        return response

    def post(self, path, data=None):
        url = self.url + path
        headers = {
            "Content-Type": "application/json",
            "accept": "*/*",
            "Accept-Language": "en-US",
        }
        headers = self.add_auth_header(headers)
        headers_string = " ".join(
            ['-H "{}: {}"'.format(k, v) for k, v in headers.items()]
        )
        data_json = json.dumps(data)
        print("curl -X POST {} {} -d {}".format(url, headers_string, data_json))
        response = requests.post(url, headers=headers, data=data_json)
        return response


class HealthIdGateway:
    def __init__(self):
        self.api = APIGateway("health", None)

    def generate_aadhaar_otp(self, data):
        path = "/v1/registration/aadhaar/generateOtp"
        response = self.api.post(path, data)
        print("{} Response: {}".format(response.status_code, response.text))
        return response.json()

    def resend_aadhaar_otp(self, data):
        path = "/v1/registration/aadhaar/resendAadhaarOtp"
        response = self.api.post(path, data)
        return response.json()

    def verify_aadhaar_otp(self, data):
        path = "/v1/registration/aadhaar/verifyOTP"
        response = self.api.post(path, data)
        return response.json()

    def generate_mobile_otp(self, data):
        path = "/v1/registration/aadhaar/generateMobileOTP"
        response = self.api.post(path, data)
        return response.json()

    # /v1/registration/aadhaar/verifyMobileOTP
    def verify_mobile_otp(self, data):
        path = "/v1/registration/aadhaar/verifyMobileOTP"
        response = self.api.post(path, data)
        return response.json()

    # /v1/registration/aadhaar/createHealthIdWithPreVerified
    def create_health_id(self, data):
        path = "/v1/registration/aadhaar/createHealthIdWithPreVerified"
        response = self.api.post(path, data)
        return response.json()


class HealthIdGatewayV2:
    def __init__(self):
        self.api = APIGateway("health", None)

    # V2 APIs
    def check_and_generate_mobile_otp(self, data):
        path = "/v2/registration/aadhaar/checkAndGenerateMobileOTP"
        response = self.api.post(path, data)
        return response.json()
