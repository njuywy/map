#!/usr/bin/env python3
"""Refresh interactive-map point features from a CGCS2000 XLSX workbook."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from convert_gcj02_to_cgcs2000 import (
    NS,
    _cell_text,
    _column_name,
    _shared_strings,
    _worksheet_paths,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_WORKBOOK = PROJECT_ROOT / "CGCS2000经纬度.xlsx"
DEFAULT_MAP_DATA = PROJECT_ROOT / "interactive-map" / "map-data.js"
DEFAULT_GEOJSON = PROJECT_ROOT / "通海铁路专用线_点位标注.geojson"
MAP_DATA_PREFIX = "window.MAP_DATA = "


def read_points(workbook: Path) -> list[dict]:
    """Read numeric lat/lng pairs from every matching worksheet in order."""
    points: list[dict] = []
    with zipfile.ZipFile(workbook) as archive:
        shared = _shared_strings(archive)
        for sheet_path in _worksheet_paths(archive):
            root = ET.fromstring(archive.read(sheet_path))
            rows = root.findall("x:sheetData/x:row", NS)
            header_index = None
            lat_column = None
            lng_column = None
            for index, row in enumerate(rows[:20]):
                headings = {}
                for cell in row.findall("x:c", NS):
                    value = _cell_text(cell, shared)
                    if value is not None:
                        headings[value.strip().lower()] = _column_name(cell.get("r", ""))
                lat_column = headings.get("lat") or headings.get("latitude") or headings.get("纬度")
                lng_column = (
                    headings.get("lng")
                    or headings.get("lon")
                    or headings.get("longitude")
                    or headings.get("经度")
                )
                if lat_column and lng_column:
                    header_index = index
                    break
            if header_index is None:
                continue

            for row in rows[header_index + 1 :]:
                cells = {
                    _column_name(cell.get("r", "")): cell
                    for cell in row.findall("x:c", NS)
                }
                try:
                    latitude = float(_cell_text(cells[lat_column], shared))
                    longitude = float(_cell_text(cells[lng_column], shared))
                except (KeyError, TypeError, ValueError):
                    continue
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError(
                        f"Invalid coordinate at {sheet_path} row {row.get('r')}: "
                        f"{latitude}, {longitude}"
                    )
                points.append(
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                        "source_sheet": sheet_path,
                        "source_row": int(row.get("r", "0")),
                    }
                )
    if not points:
        raise ValueError(f"No numeric lat/lng coordinate pairs found in {workbook}")
    return points


def load_existing_map_data(path: Path) -> dict:
    source = path.read_text(encoding="utf-8").strip()
    if not source.startswith(MAP_DATA_PREFIX) or not source.endswith(";"):
        raise ValueError(f"Unsupported map data format: {path}")
    return json.loads(source[len(MAP_DATA_PREFIX) : -1])


def point_features(points: list[dict]) -> list[dict]:
    return [
        {
            "type": "Feature",
            "properties": {
                "name": f"点位 {index}",
                "point_number": index,
                "source_row": point["source_row"],
                "source_sheet": point["source_sheet"],
                "crs": "CGCS2000 / EPSG:4490",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [point["longitude"], point["latitude"]],
            },
        }
        for index, point in enumerate(points, start=1)
    ]


def write_map_outputs(workbook: Path, map_data_path: Path, geojson_path: Path) -> int:
    points = read_points(workbook)
    map_data = load_existing_map_data(map_data_path)
    route_features = [
        feature
        for feature in map_data.get("features", [])
        if feature.get("geometry", {}).get("type") == "LineString"
    ]
    if not route_features:
        raise ValueError(f"No railway LineString features found in {map_data_path}")

    feature_collection = {
        "type": "FeatureCollection",
        "features": route_features + point_features(points),
    }
    serialized = json.dumps(feature_collection, ensure_ascii=False, indent=2)
    map_data_path.write_text(f"{MAP_DATA_PREFIX}{serialized};\n", encoding="utf-8")
    geojson_path.write_text(f"{serialized}\n", encoding="utf-8")
    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--map-data", type=Path, default=DEFAULT_MAP_DATA)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    args = parser.parse_args()
    count = write_map_outputs(args.workbook, args.map_data, args.geojson)
    print(f"Loaded {count} CGCS2000 point(s) from {args.workbook}")
    print(f"Updated {args.map_data}")
    print(f"Updated {args.geojson}")


if __name__ == "__main__":
    main()
