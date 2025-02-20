from typing import Dict, List

from fiona import Geometry
from pyproj.transformer import Transformer


def _transform_coords(coords: List, crs_transformer: Transformer) -> List[float]:
    if not coords:
        return coords
    if not isinstance(coords[0], list):
        return crs_transformer.transform(*coords)
    return [_transform_coords(coord, crs_transformer) for coord in coords]


def transform_geom(geom: Dict, crs_transformer: Transformer) -> Geometry:
    if geom["type"] == "GeometryCollection":
        return Geometry.from_dict(
            {
                **geom,
                "geometries": [
                    transform_geom(sub_geom, crs_transformer)
                    for sub_geom in geom["geometries"]
                ],
            }
        )
    return Geometry.from_dict(
        {**geom, "coordinates": _transform_coords(geom["coordinates"], crs_transformer)}
    )
