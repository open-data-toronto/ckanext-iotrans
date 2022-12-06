"""the to_file() and prune() functions
These function are the top level logic for this extension's CKAN actions
"""
import ckan.plugins.toolkit as tk
import tempfile
import os
import json
import fiona
from fiona.crs import from_epsg
from . import utils


@tk.side_effect_free
def to_file(context, data_dict):
    '''
    inputs:
        resource_id: CKAN datastore resource ID
        source_epsg: source EPSG of resource ID, if data is spatial
        target_epsgs: list of desired EPSGs of output files, if data is spatial
        target_formats: list of desired file formats

    a spatial datasets needs a geometry column
    assumes geometry column in dataset contains geometry
    assumes geometry objects within a dataset are all the same geometry type
        ex: (all Point, all Line, or all Polygon)

    outputs:
        writes desired files to folder in /tmp
        returns a list of filepaths, where the outputs are stored on disk
    '''

    # make sure an authorized user is making this call
    if not context.get("auth_user_obj", None):
        raise tk.ValidationError(
            {"constraints": ["This endpoint is for authorized accounts only"]}
        )

    # create a temp directory to store the file we create on disk
    dir_path = tempfile.mkdtemp()

    # all the outputs of this action will be stored here
    output = {}

    # Make sure a resource id is provided
    if not data_dict.get("resource_id", None):
        raise tk.ValidationError(
            {"constraints": ["Input CKAN 'resource_id' required!"]}
        )

    # make sure target_formats is provided in a list
    if not isinstance(data_dict.get("target_formats", None), list):
        raise tk.ValidationError(
            {
                "constraints": [
                    "Required input 'target_formats' be a list of strings"
                ]
            }
        )

    # Make sure the resource id provided is for a datastore resource
    resource_metadata = tk.get_action("resource_show")(
        context, {"id": data_dict["resource_id"]}
    )
    if (resource_metadata.get("datastore_active", None) in
            ["false", "False", False]):
        raise tk.ValidationError(
            {
                "constraints": [
                    data_dict["resource_id"] + " is not a datastore resource!"
                ]
            }
        )

    datastore_resource = tk.get_action("datastore_search")(
        context, {"resource_id": data_dict["resource_id"]}
    )

    # get fieldnames for the resource
    fieldnames = [field["id"] for field in datastore_resource["fields"]]
    dump_url = "http://0.0.0.0:8080/datastore/dump/" + data_dict["resource_id"]

    # create working CSV dump filepath. This file will be used for all outputs
    dump_filepath = utils.create_filepath(
        dir_path, resource_metadata["name"],
        data_dict.get("source_epsg", None), "csv"
    )
    utils.write_to_csv(
        dump_filepath, fieldnames, utils.dump_generator(dump_url, fieldnames)
    )

    # We now have our working dump file. The request tells us how to use it
    # Let's first determine whether geometry is involved

    # For geometric transformations...
    if "geometry" in fieldnames:

        if not data_dict.get("source_epsg", None):
            raise tk.ValidationError({"constraints":
                                     ["Input 'source_epsg' required!"]})

        # make sure inputs are correctly formatted
        if isinstance(data_dict.get("target_epsgs", None), int):
            data_dict["target_epsgs"] = list(data_dict["target_epsgs"])
        if isinstance(data_dict.get("target_formats", None), str):
            data_dict["target_formats"] = list(data_dict["target_formats"])

        # throw an error if input target_epsgs is not a list of integers
        if not all([isinstance(item, int)
                    for item in data_dict["target_epsgs"]]):
            raise tk.ValidationError(
                {
                    "constraints": [
                        "Input 'target_epsgs' needs to be a list of integers"
                    ]
                }
            )

        # for each target EPSG...
        for target_epsg in data_dict["target_epsgs"]:
            # for each target format...
            for target_format in data_dict["target_formats"]:

                # init fiona driver list
                drivers = {
                    "shp": "ESRI Shapefile",
                    "geojson": "GeoJSON",
                    "gpkg": "GPKG",
                }
                if (
                    target_format.lower() not in drivers.keys()
                    and target_format.lower() != "csv"
                ):
                    raise tk.ValidationError(
                        {
                            "constraints": ['''
                                "Input target_format '{target_format}' must be
                                in the following: {accepted_formats}'''.format(
                                    target_format=target_format,
                                    accepted_formats=", ".join(drivers.keys()),
                                )
                            ]
                        }
                    )

                # If the format+epsg combo match the dump, add dump to output
                if (
                    target_format.lower() == "csv"
                    and target_epsg == data_dict["source_epsg"]
                ):
                    output = utils.append_to_output(
                        output, target_format, target_epsg, dump_filepath
                    )

                # If format matches the dump but epsg doesnt...
                # ...convert the dump and add it to output
                elif (
                    target_format.lower() == "csv"
                    and target_epsg != data_dict["source_epsg"]
                ):
                    output_filepath = utils.create_filepath(
                        dir_path, resource_metadata["name"], target_epsg, "csv"
                    )
                    utils.write_to_csv(
                        output_filepath,
                        fieldnames,
                        utils.transform_dump_epsg(
                            dump_filepath,
                            fieldnames,
                            data_dict["source_epsg"],
                            target_epsg,
                        ),
                    )
                    output = utils.append_to_output(
                        output, target_format, target_epsg, output_filepath
                    )

                # if format doesnt match the dump, get fiona drivers involved
                elif target_format.lower() in drivers.keys():

                    # first, we need to build a schema
                    ckan_to_fiona_typemap = {
                        "text": "str",
                        "date": "str",
                        "timestamp": "str",
                        "float": "float",
                        "int": "int",
                    }
                    # Get Point, Line, or Polygon from the first row of data
                    # We assume all geometries in a dataset are the same type
                    geometry_type = json.loads(
                        datastore_resource["records"][0]["geometry"]
                    )["type"]
                    # Get all the field data types (other than geometry)
                    # Map them to fiona data types
                    fields_metadata = {
                        field["id"]: ckan_to_fiona_typemap[
                            "".join(
                                [char for char in field["type"]
                                    if not char.isdigit()]
                            )
                        ]
                        for field in datastore_resource["fields"]
                        if field["id"] != "geometry"
                    }
                    schema = {"geometry": geometry_type,
                              "properties": fields_metadata}
                    output_filepath = utils.create_filepath(
                        dir_path, resource_metadata["name"],
                        target_epsg, target_format)

                    if target_format.lower() != "shp":
                        with fiona.open(
                            output_filepath,
                            "w",
                            schema=schema,
                            driver=drivers[target_format],
                            crs=from_epsg(target_epsg),
                        ) as outlayer:
                            outlayer.writerecords(
                                utils.dump_to_geospatial_generator(
                                    dump_filepath,
                                    fieldnames,
                                    target_format,
                                    data_dict["source_epsg"],
                                    target_epsg,
                                )
                            )
                            outlayer.close()

                    elif target_format.lower() == "shp":
                        # Shapefiles are special

                        # By default, shapefiles are made of many files
                        # We zip those files in a single zip

                        # By default, shp colnames are renamed FIELD_#
                        # ... if their name is more than 10 characters long

                        # We dont like that, so we truncate fieldnames
                        # We make a csv mapping truncated to full colnames
                        working_schema = schema
                        working_schema["properties"] = {
                            field["id"][:10]: ckan_to_fiona_typemap[
                                "".join(
                                    [
                                        char
                                        for char in field["type"]
                                        if not char.isdigit()
                                    ]
                                )
                            ]
                            for field in datastore_resource["fields"]
                            if field["id"] != "geometry"
                        }

                        with fiona.open(
                            output_filepath,
                            "w",
                            schema=working_schema,
                            driver=drivers[target_format],
                            crs=from_epsg(target_epsg),
                        ) as outlayer:
                            outlayer.writerecords(
                                utils.dump_to_geospatial_generator(
                                    dump_filepath,
                                    fieldnames,
                                    target_format,
                                    data_dict["source_epsg"],
                                    target_epsg,
                                )
                            )
                            outlayer.close()

                        output_filepath = utils.write_to_zipped_shapefile(
                            fieldnames, dir_path,
                            resource_metadata, output_filepath
                        )

                    output = utils.append_to_output(
                        output, target_format, target_epsg, output_filepath
                    )

    # For non geometric transformations...
    elif "geometry" not in fieldnames:
        # for each target format...
        for target_format in data_dict["target_formats"]:
            output_filepath = utils.create_filepath(
                dir_path, resource_metadata["name"], None, target_format
            )

            # CSV
            if target_format.lower() == "csv":
                output = utils.append_to_output(
                    output, target_format, None, dump_filepath
                )

            # JSON
            elif target_format.lower() == "json":
                utils.write_to_json(dump_filepath,
                                    output_filepath, datastore_resource)
                output = utils.append_to_output(
                    output, target_format, None, output_filepath
                )

            # XML
            elif target_format.lower() == "xml":
                utils.write_to_xml(dump_filepath, output_filepath)
                output = utils.append_to_output(
                    output, target_format, None, output_filepath
                )

    return output


@tk.side_effect_free
def prune(context, data_dict):

    # Taken from:
    # https://github.com/open-data-toronto/iotrans/blob/master/iotrans/utils.py
    # Deletes input file or a directory as long as its in /tmp

    # make sure an authorized user is making this call
    if not context.get("auth_user_obj", None):
        raise tk.ValidationError(
            {"constraints": ["This endpoint is for authorized accounts only"]}
        )

    if not data_dict.get("path", None):
        raise tk.ValidationError(
            {"constraints": ["Input 'path' of dir/file to delete required!"]}
        )

    path = data_dict["path"]

    if not data_dict.get("path", None).startswith("/tmp/"):
        raise tk.ValidationError(
            {
                "constraints": [
                    "This action is meant for deleting folders in /tmp/ dir"
                ]
            }
        )

    if os.path.isdir(path):
        # Empty the contents of the folder before removing the directory
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))

        os.rmdir(path)
    else:
        os.remove(path)
