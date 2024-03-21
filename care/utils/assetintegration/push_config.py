"""
This module provides helper functions to push changes in asset configuration to the middleware.
"""

import requests

from care.utils.jwks.token_generator import generate_jwt


def _get_headers() -> dict:
    return {
        "Authorization": "Care_Bearer " + generate_jwt(),
        "Content-Type": "application/json",
    }


def create_asset_on_middleware(hostname: str, data: dict) -> dict:
    if not data.get("ip_address"):
        return {"error": "IP Address not provided"}
    try:
        response = requests.post(
            f"https://{hostname}/api/assets",
            json=data,
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def delete_asset_from_middleware(hostname: str, asset_id: str) -> dict:
    try:
        response = requests.delete(
            f"https://{hostname}/api/assets/{asset_id}",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def update_asset_on_middleware(hostname: str, asset_id: str, data: dict) -> dict:
    if not data.get("ip_address"):
        return {"error": "IP Address is required"}
    try:
        response = requests.put(
            f"https://{hostname}/api/assets/{asset_id}",
            json=data,
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def push_config_to_middleware(
    hostname: str,
    asset_id: str,
    data: dict,
    old_hostname: str | None = None,
) -> dict:
    if not old_hostname:
        return create_asset_on_middleware(hostname, data)
    if old_hostname != hostname:
        delete_asset_from_middleware(old_hostname, asset_id)
    return update_asset_on_middleware(hostname, asset_id, data)
