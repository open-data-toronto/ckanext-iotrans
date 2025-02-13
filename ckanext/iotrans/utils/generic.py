"""Utils functions for iotrans.py
"""

import os
from typing import Any, Dict

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


def transform_crs(geom: Dict, crs_transformer: Transformer) -> fiona.Geometry:
    """_summary_
    transform coordinates of an input geometry object
    input geometry object and pyproj transformer object
    output geometry with coordinates transformed by said transformer

    :param geom: A geometry to transform. May be a Dictionary with "type" and
        "coordinates" fields or a fiona.Geometry obj
    :type geom: Dict
    :param crs_transformer:
    :type crs_transformer: Transformer
    :raises NotImplemented: for unimplemented geometry types
    :return: transformed geometry object in the provided crs
    :rtype: fiona.Geometry
    """
    coords = geom["coordinates"]

    if geom["type"] == "Point":
        transformed_coords = crs_transformer.transform(*coords)
    elif geom["type"] == "LineString":
        transformed_coords = [crs_transformer.transform(*coord) for coord in coords]
    elif geom["type"] in ["MultiLineString", "Polygon"]:
        transformed_coords = []
        for shape in coords:
            transformed_coords += [
                [crs_transformer.transform(*coord) for coord in shape]
            ]
    else:
        raise NotImplemented(
            f"transform_crs not implemented for geom of type {geom['type']}"
        )

    return fiona.Geometry(type=geom["type"], coordinates=transformed_coords)
