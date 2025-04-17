# ruff : noqa : SLF001
from copy import deepcopy

import json_fingerprint
import simplejson as json
from django.conf import settings
from django.core.cache import cache
from json_fingerprint import hash_functions

from care.emr.fhir.client import FHIRClient

default_fhir_client = FHIRClient(server_url=settings.SNOWSTORM_DEPLOYMENT_URL)


class ResourceManger:
    _fhir_client = default_fhir_client
    resource = ""
    allowed_properties = []
    cache_prefix_key = "fhir_resource:"

    def __init__(self, fhir_client=None):
        self._filters = {}
        self._meta = {}
        self._executed = False
        if fhir_client:
            self._fhir_client = fhir_client

    def query(self, method, resource, parameters):
        payload = {"method": method, "resource": resource, "parameters": parameters}
        fingerprint = json_fingerprint.create(
            input=json.dumps(payload), hash_function=hash_functions.SHA256, version=1
        )
        cache_key = f"{self.cache_prefix_key}{fingerprint}"
        if cached_data := cache.get(cache_key):
            return cached_data
        results = self._fhir_client.query(**payload)
        cache.set(cache_key, results, 10)
        return results

    def validate_filter(self):
        pass

    def filter(self, *args, **kwargs):
        if kwargs:
            for key in kwargs:
                if key in self.allowed_properties:
                    self._filters[key] = kwargs[key]
            self.validate_filter()
        return self.clone()

    def clone(self):
        obj = self.__class__()
        obj._filters = deepcopy(self._filters)
        obj._meta = deepcopy(self._meta)
        obj._executed = self._executed
        obj._fhir_client = self._fhir_client
        return obj

    def handle_list(self, results):
        return [self.serialize(result) for result in results]

    def serialize(self, result):
        raise NotImplementedError
