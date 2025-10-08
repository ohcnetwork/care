import odoorpc
import base64
import requests
import json
import logging
from django.conf import settings
from rest_framework.exceptions import ValidationError


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
            f"{settings.ODOO_CONFIG['username']}:{settings.ODOO_CONFIG['password']}:{settings.ODOO_CONFIG['database']}".encode()
        ).decode()

        # Always use http/https for API calls regardless of odoorpc protocol setting
        protocol = "https" if settings.ODOO_CONFIG.get("protocol") == "https" else "http"
        url_old = f"{protocol}://{settings.ODOO_CONFIG['host']}:{settings.ODOO_CONFIG['port']}{endpoint}"

        url = "https://odoo.ohc.network/api/create_invoice"
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "db": settings.ODOO_CONFIG["database"],
        }


        # Log curl equivalent for debugging
        try:
            headers_str = ' '.join([f"-H '{k}: {v}'" for k,v in headers.items()])
            data_str = f"-d '{json.dumps(data)}'" if data else ""
            curl_command = f"curl -X POST {headers_str} {data_str} '{url}'"
            logging.info(f"Equivalent curl command:\n{curl_command}")
        except Exception as e:
            logging.info(e)


        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

        except Exception as e:
            logging.info(e)
            raise ValidationError({"error": "Error connecting to Odoo API"})

        # Handle JSON-RPC response format
        response_json = response.json()
        try:
            if response_json.get("result", {}).get("success"):
                return response_json
            else:
                logging.info(f"Error response from Odoo API: {response_json}")
                raise ValidationError({"error": "Invalid response from Odoo API"})
        except Exception as e:
            logging.info(e)
            raise ValidationError({"error": "Error response from Odoo API"})


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
