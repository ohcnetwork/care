import base64
import json
import logging

import odoorpc
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class OdooConnector:
    connection = None
    is_authenticated = False

    @classmethod
    def get_connection(cls):
        if not cls.connection:
            cls.connection = odoorpc.ODOO(
                settings.ODOO_CONFIG["host"],
                port=settings.ODOO_CONFIG["port"],
                protocol=settings.ODOO_CONFIG["protocol"],
            )
            cls.connection.login(
                settings.ODOO_CONFIG["database"],
                settings.ODOO_CONFIG["username"],
                settings.ODOO_CONFIG["password"],
            )
            cls.validate_connection()
        return cls.connection

    @classmethod
    def call_api(cls, endpoint: str, data: dict) -> dict:
        """Call a custom Odoo addon API endpoint.

        Args:
            endpoint: The API endpoint path (e.g. '/api/create_invoice')
            data: The data to send in the request body

        Returns:
            dict: The JSON response from the API
        """
        # Include database name in credentials for Odoo session authentication
        auth = base64.b64encode(
            f"{settings.ODOO_CONFIG['username']}:{settings.ODOO_CONFIG['password']}".encode()
        ).decode()

        # # Always use http/https for API calls regardless of odoorpc protocol setting
        # protocol = (
        #     "https" if settings.ODOO_CONFIG.get("protocol") == "https" else "http"
        # )
        # url_old = f"{protocol}://{settings.ODOO_CONFIG['host']}:{settings.ODOO_CONFIG['port']}{endpoint}"

        # digital ocean
        # url = f"https://odoo.ohc.network/{endpoint}"

        # local
        # url = f"http://host.docker.internal:8069/{endpoint}"

        url = f"{settings.ODOO_CONFIG['protocol']}://{settings.ODOO_CONFIG['host']}"
        if settings.ODOO_CONFIG["port"]:
            url += f":{settings.ODOO_CONFIG['port']}"
        url += f"/{endpoint}"

        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "db": settings.ODOO_CONFIG["database"],
        }

        # Log curl equivalent for debugging
        try:
            headers_str = " ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
            data_str = f"-d '{json.dumps(data)}'" if data else ""
            curl_command = f"curl -X POST {headers_str} {data_str} '{url}'"
            logger.info("Equivalent curl command:\n%s", curl_command)
        except Exception as e:
            logger.info(e)

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response_json = response.json()
            logger.info("Odoo API Response: %s", response_json)

            if not response.ok:
                error_msg = response_json.get("message", str(response.reason))
                logger.exception("Odoo API Error: %s", error_msg)
                response.raise_for_status()  # This will raise HTTPError with proper status code

            return response_json
        except requests.exceptions.RequestException as e:
            logger.exception("Odoo API Error: %s", str(e))
            raise ValidationError(str(e)) from e

    @classmethod
    def validate_connection(cls):
        if not cls.connection.env.user:
            cls.is_authenticated = False
        else:
            cls.is_authenticated = True

    @classmethod
    def get_model(cls, model_name: str):
        cls.get_connection()
        return cls.connection.env[model_name]
