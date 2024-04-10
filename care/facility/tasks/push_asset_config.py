"""
This module provides helper functions to push changes in asset configuration to the middleware.
"""

from logging import Logger

import requests
from celery import shared_task
from celery.utils.log import get_task_logger

from care.utils.jwks.token_generator import generate_jwt

logger: Logger = get_task_logger(__name__)


def _get_headers() -> dict:
    return {
        "Authorization": "Care_Bearer " + generate_jwt(),
        "Content-Type": "application/json",
    }


def create_asset_on_middleware(hostname: str, data: dict) -> dict:
    if not data.get("ip_address"):
        logger.error("IP Address is required")
    try:
        response = requests.post(
            f"https://{hostname}/api/assets",
            json=data,
            headers=_get_headers(),
            timeout=25,
        )
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Pushed Asset Configuration to Middleware: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error Pushing Asset Configuration to Middleware: {e}")
        return {"error": str(e)}


def delete_asset_from_middleware(hostname: str, asset_id: str) -> dict:
    try:
        response = requests.delete(
            f"https://{hostname}/api/assets/{asset_id}",
            headers=_get_headers(),
            timeout=25,
        )
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Deleted Asset from Middleware: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error Deleting Asset from Middleware: {e}")
        return {"error": str(e)}


def update_asset_on_middleware(hostname: str, asset_id: str, data: dict) -> dict:
    if not data.get("ip_address"):
        logger.error("IP Address is required")
        return {"error": "IP Address is required"}
    try:
        response = requests.put(
            f"https://{hostname}/api/assets/{asset_id}",
            json=data,
            headers=_get_headers(),
            timeout=25,
        )
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Updated Asset Configuration on Middleware: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error Updating Asset Configuration on Middleware: {e}")
        return {"error": str(e)}


@shared_task
def push_config_to_middleware_task(
    hostname: str,
    asset_id: str,
    data: dict,
    old_hostname: str | None = None,
) -> dict:
    if not old_hostname:
        create_asset_on_middleware(hostname, data)
    if old_hostname != hostname:
        delete_asset_from_middleware(old_hostname, asset_id)
    return update_asset_on_middleware(hostname, asset_id, data)


@shared_task
def delete_asset_from_middleware_task(hostname: str, asset_id: str) -> dict:
    return delete_asset_from_middleware(hostname, asset_id)
