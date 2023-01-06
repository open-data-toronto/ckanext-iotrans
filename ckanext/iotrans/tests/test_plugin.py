"""
Test module for various iotrans functions
"""

import ckanext.iotrans.utils as utils
import filecmp
import json
import os
import pytest

# Define fixed variables
test_dir_path = os.path.dirname(os.path.realpath(__file__))
test_tmp_path = "/tmp/iotrans_test_folder/"

# Define fixtures


@pytest.fixture
def test_filepath_with_epsg():
    return utils.create_filepath(test_tmp_path + "",
                                 "resource_name", 4326, "csv")


@pytest.fixture
def test_filepath_no_epsg():
    return utils.create_filepath(test_tmp_path + "",
                                 "resource_name", None, "csv")


@pytest.fixture
def test_dump_json_filepath():
    correct_dump_csv_filepath = test_dir_path + "/correct_dump.csv"
    filepath = test_dir_path + "/test_dump.json"
    if os.path.exists(filepath):
        os.remove(filepath)
    with open(test_dir_path + "/correct_datastore_resource.json") as jsonfile:
        correct_datastore_resource = json.load(jsonfile)
        utils.write_to_json(correct_dump_csv_filepath,
                            filepath,
                            correct_datastore_resource)
    return filepath


@pytest.fixture
def test_dump_xml_filepath():
    correct_dump_csv_filepath = test_dir_path + "/correct_dump.csv"
    filepath = test_dir_path + "/test_dump.xml"
    if os.path.exists(filepath):
        os.remove(filepath)
    utils.write_to_xml(correct_dump_csv_filepath, filepath)
    return filepath


@pytest.fixture
def correct_geospatial_generator():
    correct_spatial_dump_csv_filepath = test_dir_path + "/correct_geo_dump.csv"
    correct_spatial_csv_dump_fieldnames = [
        "service_system_manager",
        "agency",
        "loc_id",
        "program_name",
        "serviceName",
        "buildingName",
        "address",
        "full_address",
        "major_intersection",
        "ward",
        "ward_name",
        "located_in_school",
        "school_name",
        "geometry",
        "centre_type",
    ]

    return utils.dump_to_geospatial_generator(
        correct_spatial_dump_csv_filepath,
        correct_spatial_csv_dump_fieldnames,
        "geojson",
        4326,
        2952
    )


def test_create_filepath_with_epsg(test_filepath_with_epsg):
    """test case for utils.create_filepath with an input epsg"""
    correct_filepath_with_epsg = test_tmp_path + "resource_name - 4326.csv"

    assert correct_filepath_with_epsg == test_filepath_with_epsg


def test_create_filepath_without_epsg(test_filepath_no_epsg):
    """test case for utils.create_filepath without an input epsg"""
    correct_filepath_without_epsg = test_tmp_path + "resource_name.csv"

    assert correct_filepath_without_epsg == test_filepath_no_epsg


def test_write_to_json(test_dump_json_filepath):
    """test case for utils.write_to_json"""
    correct_dump_json_filepath = test_dir_path + "/correct_dump.json"
    assert filecmp.cmp(test_dump_json_filepath, correct_dump_json_filepath)


def test_write_to_xml(test_dump_xml_filepath):
    """test case for utils.write_to_xml"""
    correct_dump_xml_filepath = test_dir_path + "/correct_dump.xml"
    assert filecmp.cmp(test_dump_xml_filepath, correct_dump_xml_filepath)


def test_dump_to_geospatial_generator(correct_geospatial_generator):
    """checks if generator made by utils.dump_to_geospatial_generator
    contains dicts with valid, non-empty data"""
    for item in correct_geospatial_generator:
        assert isinstance(item["properties"], dict)
        assert len(item["properties"])
        assert isinstance(item["geometry"], dict)
        assert len(item["geometry"])
