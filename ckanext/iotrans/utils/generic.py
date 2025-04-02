"""Utils functions for iotrans.py
"""

import os
from typing import Any, Callable, TypeVar, Union

import ckan.plugins.toolkit as tk
import fiona
from pyproj.transformer import Transformer


def is_falsey(arg: Any) -> bool:
    return arg in ["false", "False", False]


def dump_generator(resource_id, context):
    """reads a CKAN datastore_search calls, returns a python generator"""
    # init some vars
    chunk = 20000
    i = 0

    while True:
        # get a chunk of records from datastore resource
        records = tk.get_action("datastore_search")(
            context,
            {
                "resource_id": resource_id,
                "limit": chunk,
                "offset": chunk * i,
            },
        )["records"]

        if len(records):
            for record in records:
                yield record
            i += 1
            continue

        else:
            break


def get_filepath(dir_path, resource_name, epsg, file_format):
    """Gets a filepath using input resource name, and desired format/epsg"""

    epsg_suffix = " - " + str(epsg) if epsg else ""
    return os.path.join(
        dir_path, "{0}{1}.{2}".format(resource_name, epsg_suffix, file_format.lower())
    )


def iotrans_auth_function(context, data_dict=None):
    """CKAN auth function - requires authorized uses for certain actions"""
    is_authorized = context.get("auth_user_obj", False)

    if is_authorized:
        return {"success": True}
    else:
        return {
            "success": False,
            "msg": "This endpoint is for authorized accounts only",
        }


GroupByT = TypeVar("PartiontionByT")
DictKey = Union[str, int, tuple, bool]


def stable_group_by(
    items: list[GroupByT], key_func: Callable[[GroupByT], DictKey]
) -> list[list[GroupByT]]:
    result: list[dict[DictKey, GroupByT]] = []

    for item in items:
        last_group = result[-1] if len(result) else None

        key = key_func(item)
        if last_group is None or key != last_group["key"]:
            group = {"key": key, "items": [item]}
            result.append(group)
        else:
            last_group["items"].append(item)
    return result
