"""
Test module for various iotrans functions
"""

import os

import pytest
from fiona import Geometry
from pyproj.transformer import TransformerGroup

from ckanext.iotrans.utils import generic, to_file, transform

from .utils import TEST_TMP_PATH


def test_create_filepath_with_epsg():
    """test case for utils.create_filepath with an input epsg"""
    correct_filepath_with_epsg = os.path.join(TEST_TMP_PATH, "resource_name - 4326.csv")
    test_filepath_with_epsg = generic.get_filepath(
        TEST_TMP_PATH, "resource_name", 4326, "csv"
    )

    assert correct_filepath_with_epsg == test_filepath_with_epsg


def test_create_filepath_without_epsg():
    """test case for utils.create_filepath without an input epsg"""
    correct_filepath_without_epsg = os.path.join(TEST_TMP_PATH, "resource_name.csv")
    test_filepath_no_epsg = generic.get_filepath(
        TEST_TMP_PATH, "resource_name", None, "csv"
    )

    assert correct_filepath_without_epsg == test_filepath_no_epsg


@pytest.mark.parametrize(
    "batch_size,n_full_batches,additional",
    [
        (3, 2, 0),  # 2 full batches
        (3, 2, 1),  # 2 full batches + 1 partial batch
        (3, 0, 2),  # 0 batches + 1 partial batch
        (3, 0, 0),  # 0 records
    ],
)
def test_batched(batch_size, n_full_batches, additional):

    n_expected = batch_size * n_full_batches + additional
    generator = range(n_expected)
    expected_items = list(range(n_expected))

    items = []
    for batch in to_file._batched(generator, batch_size):
        for item in batch:
            items.append(item)

    assert items == expected_items


class TestTransformCRS:
    """test cases for converting coordinates from 4326 to 2952"""

    crs_transformer = TransformerGroup(
        "EPSG:4326", "EPSG:2952", always_xy=True
    ).transformers[1]

    def test_point(self):
        point = {"type": "Point", "coordinates": [-79.2428222353868, 43.8119927252015]}
        correct_point = Geometry(
            type="Point",
            coordinates=(325490.2070075939, 4852479.658328905),
        )

        assert correct_point == transform.transform_geom(point, self.crs_transformer)

    def test_line_string(self):
        line = {
            "type": "LineString",
            "coordinates": [
                [-79.3019103400789, 43.6357339848196],
                [-79.5011710561479, 43.6358913119773],
            ],
        }
        correct_line = Geometry(
            type="LineString",
            coordinates=[
                (320783.3024109413, 4832884.982596695),
                (304705.51100000145, 4832883.394895321),
            ],
        )

        assert correct_line == transform.transform_geom(line, self.crs_transformer)

    def test_multi_line_string(self):
        multiline = {
            "type": "MultiLineString",
            "coordinates": [
                [
                    [-79.5200422810281, 43.6570082724531],
                    [-79.5197460507363, 43.6572140858806],
                    [-79.5196635775072, 43.6572838605627],
                    [-79.5196044400535, 43.6573627315499],
                    [-79.5195622136557, 43.657442634768],
                    [-79.5195116632469, 43.6575459158964],
                    [-79.5194644862472, 43.6576532650363],
                    [-79.5192567794767, 43.6579952164758],
                ],
                [
                    [-79.5192567794767, 43.6579952164758],
                    [-79.5192953674878, 43.6578174693239],
                    [-79.5192824544575, 43.6577192667785],
                    [-79.5192437843152, 43.6576397643725],
                    [-79.5191664587174, 43.6575649491419],
                    [-79.5190569182772, 43.6575135337418],
                    [-79.5189216376394, 43.6574948424072],
                    [-79.5187863753207, 43.6574948737175],
                    [-79.5184643221714, 43.6575276731014],
                ],
                [
                    [-79.5192567794767, 43.6579952164758],
                    [-79.5192295701625, 43.6580483290164],
                    [-79.5191465294085, 43.6582103942419],
                    [-79.5190683957878, 43.6584441633269],
                    [-79.5190403597176, 43.6586285696233],
                    [-79.5189925692403, 43.65891902407],
                    [-79.5189370433764, 43.6591752926463],
                    [-79.5188586943168, 43.6594007443395],
                    [-79.5186381156228, 43.6599662271059],
                    [-79.5186119236932, 43.6603072293588],
                ],
            ],
        }
        correct_multiline = Geometry(
            type="MultiLineString",
            coordinates=[
                [
                    (303183.41499997803, 4835229.561895318),
                    (303207.31399997947, 4835252.420895317),
                    (303213.96799997805, 4835260.170895319),
                    (303218.7399999751, 4835268.9318953175),
                    (303222.1479999749, 4835277.807895315),
                    (303226.22799997334, 4835289.280895316),
                    (303230.03599997686, 4835301.205895314),
                    (303246.79799997417, 4835339.190895317),
                ],
                [
                    (303246.79799997417, 4835339.190895317),
                    (303243.68099997577, 4835319.4448953215),
                    (303244.7199999746, 4835308.534895316),
                    (303247.83699997264, 4835299.701895319),
                    (303254.0719999742, 4835291.388895315),
                    (303262.9059999732, 4835285.674895322),
                    (303273.81699997536, 4835283.595895324),
                    (303284.7269999723, 4835283.596895317),
                    (303310.7039999776, 4835287.234895322),
                ],
                [
                    (303246.79799997417, 4835339.190895317),
                    (303248.99399997207, 4835345.090895312),
                    (303255.6959999748, 4835363.093895318),
                    (303262.00399997336, 4835389.062895315),
                    (303264.2699999775, 4835409.548895313),
                    (303268.13199998013, 4835441.815895315),
                    (303272.6169999734, 4835470.284895315),
                    (303278.9419999765, 4835495.32989532),
                    (303296.746999975, 4835558.14789532),
                    (303298.86799997394, 4835596.03089532),
                ],
            ],
        )

        assert correct_multiline == transform.transform_geom(
            multiline, self.crs_transformer
        )

    def test_polygon(self):
        polygon = {
            "coordinates": [
                [
                    [-79.4910534106931, 43.7635021528307],
                    [-79.4900820250133, 43.7598284098823],
                    [-79.4899806571011, 43.7593255316339],
                    [-79.4896582169971, 43.7580571182177],
                    [-79.4894943462708, 43.7574480826525],
                    [-79.4892217914919, 43.7563581298315],
                ]
            ],
            "type": "Polygon",
        }
        correct_polygon = Geometry(
            type="Polygon",
            coordinates=[
                [
                    (305520.3440000078, 4847060.393895305),
                    (305598.60500001657, 4846652.262895307),
                    (305606.7740000103, 4846596.395895303),
                    (305632.75500001136, 4846455.482895307),
                    (305645.9590000174, 4846387.822895305),
                    (305667.9220000117, 4846266.735895304),
                ]
            ],
        )

        assert correct_polygon == transform.transform_geom(
            polygon, self.crs_transformer
        )

    def test_preserves_z_axis(self):
        geom = Geometry(
            type="MultiLineString",
            coordinates=[[[0, 0, 1], [0, 0, 2]], [[0, 0, 3], [0, 0, 4]]],
        )
        transformed = transform.transform_geom(geom, self.crs_transformer)
        z_coords = [point[2] for string in transformed.coordinates for point in string]
        assert z_coords == [1, 2, 3, 4]

    @pytest.mark.parametrize(
        "geometry",
        (
            Geometry(type="Point", coordinates=[0.0, 0.0]),
            Geometry(type="MultiPoint", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
            Geometry(type="LineString", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
            Geometry(
                type="MultiLineString",
                coordinates=[[[0.0, 0.0], [1.0, 1.0]], [[2.0, 2.0], [3.0, 3.0]]],
            ),
            Geometry(
                type="Polygon",
                coordinates=[
                    [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
                ],
            ),
            Geometry(
                type="MultiPolygon",
                coordinates=[
                    [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
                    [[[2.0, 2.0], [3.0, 2.0], [3.0, 3.0], [2.0, 3.0], [2.0, 2.0]]],
                ],
            ),
            Geometry(
                type="GeometryCollection",
                geometries=[
                    Geometry(type="Point", coordinates=[0.0, 0.0]),
                    Geometry(type="LineString", coordinates=[[0.0, 0.0], [1.0, 1.0]]),
                ],
            ),
        ),
    )
    def test_geometry_type_coverage(self, geometry):
        class MockTransformer:
            @staticmethod
            def transform(*coords):
                return list(coords)

        transformed = transform.transform_geom(geometry, MockTransformer())
        assert dict(transformed) == geometry


_is_even = lambda x: x % 2 == 0
_mod_3 = lambda x: x % 3


@pytest.mark.parametrize(
    "items,key_func,expected",
    [
        # all 1 group
        ([0, 0], _is_even, [{"key": True, "items": [0, 0]}]),
        # 2 groups
        (
            [0, 1],
            _is_even,
            [{"key": True, "items": [0]}, {"key": False, "items": [1]}],
        ),
        # preserving order when changes back and forth between 2 groups
        (
            [0, 1, 2, 4, 5],
            _is_even,
            [
                {"key": True, "items": [0]},
                {"key": False, "items": [1]},
                {"key": True, "items": [2, 4]},
                {"key": False, "items": [5]},
            ],
        ),
        # empty case
        ([], _is_even, []),
        # 3 groups
        (
            [0, 1, 2, 3, 3, 3, 4, 5],
            _mod_3,
            [
                {"key": 0, "items": [0]},
                {"key": 1, "items": [1]},
                {"key": 2, "items": [2]},
                {"key": 0, "items": [3, 3, 3]},
                {"key": 1, "items": [4]},
                {"key": 2, "items": [5]},
            ],
        ),
    ],
)
def test_stable_group_by(items, key_func, expected):
    result = generic.stable_group_by(items, key_func)
    assert expected == result
