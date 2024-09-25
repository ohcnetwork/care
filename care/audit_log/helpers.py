# ruff: noqa: SLF001
import re
from fnmatch import fnmatch
from functools import lru_cache
from typing import NamedTuple

from django.conf import settings
from rest_framework.utils.encoders import JSONEncoder


def remove_non_member_fields(d: dict):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def instance_finder(v):
    return isinstance(
        v,
        list | dict | set,
    )


def seperate_hashable_dict(d: dict):
    non_hashable = {k: v for k, v in d.items() if instance_finder(v)}
    hashable = {k: v for k, v in d.items() if k not in non_hashable}
    return hashable, non_hashable


def get_or_create_meta(instance):
    if not hasattr(instance._meta, "dal"):
        instance._meta.dal = MetaDataContainer()
    return instance


def get_model_name(instance):
    return f"{instance._meta.app_label}.{instance.__class__.__name__}"


class Search(NamedTuple):
    type: str
    value: str


def _make_search(item):
    splits = item.split(":")
    if len(splits) == 2:  # noqa: PLR2004
        return Search(type=splits[0], value=splits[1])
    return Search(type="plain", value=splits[0])


def candidate_in_scope(
    candidate: str, scope: list, is_application: bool = False
) -> bool:
    """
    Check if the candidate string is valid with the scope supplied,
    the scope should be list of search strings - that can be either
    glob, plain or regex

    :param candidate: search string
    :param scope: List of Search
    :return: valid?
    """
    search_candidate = candidate
    if is_application:
        splits = candidate.split(".")
        if len(splits) == 2:  # noqa: PLR2004
            app_label, model_name = splits
            search_candidate = app_label

    for item in scope:
        match = False
        search = _make_search(item)
        if search.type == "glob":
            match = fnmatch(search_candidate.lower(), search.value.lower())
        if search.type == "plain":
            match = search_candidate.lower() == search.value.lower()
        if search.type == "regex":
            match = bool(re.match(search.value, search_candidate, re.IGNORECASE))

        if match:
            return True

    return False


@lru_cache
def exclude_model(model_name):
    if candidate_in_scope(
        model_name,
        settings.AUDIT_LOG["globals"]["exclude"]["applications"],
        is_application=True,
    ):
        return True

    return bool(
        candidate_in_scope(
            model_name, settings.AUDIT_LOG["models"]["exclude"]["models"]
        )
    )


class MetaDataContainer(dict):
    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        self[key] = value


class LogJsonEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)
