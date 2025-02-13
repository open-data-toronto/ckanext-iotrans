"""
For profiling memory usage.
Note: this may not be totally appropriate as a `test` per-se, however, at the time of
writing it is the most ergonomic way to:
- scaffold some temporary ckan resources
- load into a ckan context
- run a ckan action
- cleanup any temporarily created resources
"""

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Generator

import psutil
import pytest
from ckan.common import config
from fiona import Feature
from iotrans.utils.to_file import (
    EPSG,
    DatastoreResourceMetadata,
    SpatialToCsv,
    SpatialToShp,
    SpatialToSpatial,
)

random.seed(42)


def _get_mock_coordinates(epsg: EPSG):
    if epsg == 4326:
        longitude = round(random.uniform(-79.57696424675612, -79.26458445595404), 6)
        latitude = round(random.uniform(43.723463973559376, 43.75993665224853), 6)
        return [longitude, latitude]
    elif epsg == 2952:
        return [
            # 0m - 500km
            round(random.uniform(0, 500000), 6),
            # 0m - 5000km
            round(random.uniform(0, 5000000), 6),
        ]
    raise ValueError(f"epsg {epsg} not recognized")


def _geom_generator(epsg: EPSG, num_rows: int) -> Generator[Feature, None, None]:
    for record_id in range(num_rows):
        start_date = datetime.now() - timedelta(days=3650)
        random_date = start_date + timedelta(days=random.randint(0, 3650))

        geometry = {"type": "Point", "coordinates": _get_mock_coordinates(epsg)}

        yield {
            "geometry": json.dumps(geometry),
            "text_field": "some text",
            "json_field": json.dumps({"a": 2, "b": 4}),
            "date_field": str(random_date.date),
            "time_field": random_date.isoformat(),
            "timestamp_field": random_date.timestamp(),
            "int_field": record_id,
            "float_field": 1.0,
            "bool_field": True,
        }


@pytest.fixture(scope="session")
def fiona_logger():
    logger = logging.getLogger()  # Get the root logger
    logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    now = datetime.now().isoformat()
    file_handler = logging.FileHandler(
        os.path.join(os.path.dirname(__file__), f"{now}.log")
    )
    logger.addHandler(file_handler)

    # Optionally, may want to log fiona info:
    # logging.getLogger("fiona.ogrext").setLevel(logging.DEBUG)

    return logger


def log_memory_usage(logger, process, i, n_rows, min_memory, max_memory):
    mem_info = process.memory_full_info()
    memory_usage_mb = mem_info.rss / (1024 * 1024)
    swap_usage_mb = mem_info.swap / (1024 * 1024)
    min_memory = min(
        memory_usage_mb, float("inf") if min_memory is None else min_memory
    )
    max_memory = max(
        memory_usage_mb, float("-inf") if max_memory is None else max_memory
    )
    num_fmt = "{:.10f}"
    logger.debug(
        f"iters: {i}/{n_rows} ({'{:.1f}'.format(i*100/n_rows)}%), "
        f"mem: {num_fmt.format(memory_usage_mb)}MB, "
        f"min: {num_fmt.format(min_memory)}MB, "
        f"max: {num_fmt.format(max_memory)}MB, "
        f"swap: {num_fmt.format(swap_usage_mb)}MB, "
    )
    return memory_usage_mb, min_memory, max_memory


@pytest.fixture()
def tmp_ckan_disk_path():
    index = 0
    storage_path = config.get("ckan.storage_path")
    path = os.path.join(storage_path, "tmp-pytest", f"test_{index}")
    while os.path.exists(path):
        index += 1
        path = os.path.join(storage_path, "tmp-pytest", f"test_{index}")
    os.makedirs(path)
    try:
        yield path
    finally:
        import shutil

        shutil.rmtree(path)


@pytest.mark.parametrize(
    "n_rows,handler_cls,target_format,source_epsg,target_epsg",
    [
        # shp files
        # NOTE: shp files have an inherent size limitation of 2GB so if performing
        #   profiling for shp cases here we use fewer n_rows. Empirically, this is about
        #   the max n_rows we can get before getting an error due to the shp file size
        (4_130_001, SpatialToShp, "shp", 4326, 4326),
        (1_000_001, SpatialToShp, "shp", 4326, 2952),
        # csvs
        (10_000_001, SpatialToCsv, "csv", 4326, 4326),
        (10_000_001, SpatialToCsv, "csv", 4326, 2952),
        # geojson
        (10_000_001, SpatialToSpatial, "geojson", 4326, 4326),
        (10_000_001, SpatialToSpatial, "geojson", 4326, 2952),
        (10_000_001, SpatialToSpatial, "geojson", 2952, 4326),
        # gpkg
        (10_000_001, SpatialToSpatial, "gpkg", 4326, 4326),
        (10_000_001, SpatialToSpatial, "gpkg", 4326, 2952),
    ],
)
@pytest.mark.skipif(
    os.environ.get("IOTRANS_TEST_PROFILE") != "1",
    reason="Profiling test skipped by default, set `IOTRANS_TEST_PROFILE=1` to profile",
)
def test_profile_spatial_files(
    n_rows,
    handler_cls,
    target_format,
    source_epsg,
    target_epsg,
    tmp_ckan_disk_path,
    fiona_logger,
):
    output_filepath = os.path.join(tmp_ckan_disk_path, "out")
    datastore_metadata: DatastoreResourceMetadata = {
        "fields": [
            # Must have a geometry text col
            {"type": "text", "id": "geometry"},
            # All other possible types from here:
            # https://docs.ckan.org/en/2.9/maintaining/datastore.html#valid-types
            {"type": "text", "id": "text_field"},
            {"type": "json", "id": "json_field"},
            {"type": "date", "id": "date_field"},
            {"type": "time", "id": "time_field"},
            {"type": "timestamp", "id": "timestamp_field"},
            {"type": "int", "id": "int_field"},
            {"type": "float", "id": "float_field"},
            {"type": "bool", "id": "bool_field"},
        ],
        "geometry_type": "Point",
        "name": "test-resource",
    }

    pid = os.getpid()
    process = psutil.Process(pid)
    fiona_logger.debug(f"Pid: {pid}")

    for s in [
        f"  when: {datetime.now().isoformat()}",
        f"  handler_cls: {handler_cls}",
        f"  target_format: {target_format}",
        f"  source_epsg: {source_epsg}",
        f"  target_epsg: {target_epsg}",
        f"  tmp_disk_path: {tmp_ckan_disk_path}",
    ]:
        fiona_logger.debug(s)

    min_memory = None
    max_memory = None

    profile_every = 10_000

    def row_generator():
        nonlocal min_memory
        nonlocal max_memory

        for i, row in enumerate(_geom_generator(epsg=source_epsg, num_rows=n_rows)):
            if i % profile_every == 0:
                memory_usage_mb, min_memory, max_memory = log_memory_usage(
                    fiona_logger, process, i, n_rows, min_memory, max_memory
                )
                assert memory_usage_mb < 4000, "Too much memory!"
            i += 1
            yield row
        # (Note this is approximate and misses the last reading)
        return min_memory, max_memory

    handler = handler_cls(
        source_epsg=source_epsg,
        target_epsg=target_epsg,
        target_format=target_format,
        output_filepath=output_filepath,
        datastore_metadata=datastore_metadata,
    )

    result = handler.to_file(row_generator())

    for s in [
        f"  min_memory: {min_memory}",
        f"  max_memory: {max_memory}",
    ]:
        fiona_logger.debug(s)

    fiona_logger.debug(result)
