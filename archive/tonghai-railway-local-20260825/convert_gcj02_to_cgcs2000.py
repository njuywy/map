#!/usr/bin/env python3
"""Convert GCJ-02 latitude/longitude cells in an XLSX workbook to CGCS2000.

The workbook is copied without changing its layout.  Worksheets containing
``lat`` and ``lng``/``lon`` headers are detected automatically, and numeric
coordinate pairs below those headers are replaced with CGCS2000 coordinates.

GCJ-02 is inverted iteratively against its commonly used forward model.  At
the requested metre-level accuracy, the recovered global geodetic latitude
and longitude can be expressed directly in CGCS2000 (EPSG:4490); the WGS 84
and CGCS2000 ellipsoid difference is far below one metre for this purpose.
"""

from __future__ import annotations

import argparse
import math
import os
import posixpath
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"x": MAIN_NS, "r": REL_NS, "pr": PKG_REL_NS}
ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)

PI = math.pi
GCJ_A = 6378245.0
GCJ_EE = 0.00669342162296594323


def _outside_china(lat: float, lng: float) -> bool:
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(x: float, y: float) -> float:
    value = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y
    value += 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    value += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    value += (160.0 * math.sin(y / 12.0 * PI) + 320.0 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return value


def _transform_lng(x: float, y: float) -> float:
    value = 300.0 + x + 2.0 * y + 0.1 * x * x
    value += 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    value += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    value += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return value


def global_to_gcj02(lat: float, lng: float) -> tuple[float, float]:
    """Apply the standard GCJ-02 forward model to global geodetic coordinates."""
    if _outside_china(lat, lng):
        return lat, lng
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * PI
    magic = 1.0 - GCJ_EE * math.sin(rad_lat) ** 2
    sqrt_magic = math.sqrt(magic)
    d_lat = d_lat * 180.0 / ((GCJ_A * (1.0 - GCJ_EE)) / (magic * sqrt_magic) * PI)
    d_lng = d_lng * 180.0 / (GCJ_A / sqrt_magic * math.cos(rad_lat) * PI)
    return lat + d_lat, lng + d_lng


def gcj02_to_cgcs2000(lat: float, lng: float) -> tuple[float, float, int, float]:
    """Invert GCJ-02 by fixed-point iteration and return a closure residual."""
    if _outside_china(lat, lng):
        return lat, lng, 0, 0.0
    result_lat, result_lng = lat, lng
    iterations = 0
    for iterations in range(1, 31):
        check_lat, check_lng = global_to_gcj02(result_lat, result_lng)
        error_lat = check_lat - lat
        error_lng = check_lng - lng
        result_lat -= error_lat
        result_lng -= error_lng
        if max(abs(error_lat), abs(error_lng)) < 1e-12:
            break
    check_lat, check_lng = global_to_gcj02(result_lat, result_lng)
    mean_lat = math.radians((lat + check_lat) / 2.0)
    north_m = (check_lat - lat) * 111132.92
    east_m = (check_lng - lng) * 111412.84 * math.cos(mean_lat)
    residual_m = math.hypot(north_m, east_m)
    return result_lat, result_lng, iterations, residual_m


def _column_name(cell_ref: str) -> str:
    return "".join(ch for ch in cell_ref if ch.isalpha()).upper()


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    result = []
    for item in root.findall("x:si", NS):
        result.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return result


def _cell_text(cell: ET.Element, shared: list[str]) -> str | None:
    value = cell.find("x:v", NS)
    if value is None or value.text is None:
        return None
    if cell.get("t") == "s":
        return shared[int(value.text)]
    return value.text


def _worksheet_paths(archive: zipfile.ZipFile) -> list[str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.get("Id"): rel.get("Target")
        for rel in relationships.findall("pr:Relationship", NS)
    }
    paths = []
    package_parts = set(archive.namelist())
    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        target = targets.get(sheet.get(f"{{{REL_NS}}}id"))
        if target:
            if target.startswith("/"):
                path = posixpath.normpath(target.lstrip("/"))
            else:
                path = posixpath.normpath(posixpath.join("xl", target))

            # Some producers write package-root-relative targets without the
            # leading slash. Keep compatibility with those workbooks while
            # resolving standards-compliant targets relative to workbook.xml.
            root_relative_path = posixpath.normpath(target.lstrip("/"))
            if path not in package_parts and root_relative_path in package_parts:
                path = root_relative_path
            paths.append(path)
    return paths


def _convert_sheet(xml_data: bytes, shared: list[str]) -> tuple[bytes, list[dict[str, float | int]]]:
    root = ET.fromstring(xml_data)
    rows = root.findall("x:sheetData/x:row", NS)
    if not rows:
        return xml_data, []

    header_row_index = None
    lat_column = None
    lng_column = None
    for row_index, row in enumerate(rows[:20]):
        headings = {}
        for cell in row.findall("x:c", NS):
            text = _cell_text(cell, shared)
            if text is not None:
                headings[text.strip().lower()] = _column_name(cell.get("r", ""))
        lat_column = headings.get("lat") or headings.get("latitude") or headings.get("纬度")
        lng_column = (
            headings.get("lng") or headings.get("lon") or headings.get("longitude") or headings.get("经度")
        )
        if lat_column and lng_column:
            header_row_index = row_index
            break
    if header_row_index is None:
        return xml_data, []

    converted = []
    for row in rows[header_row_index + 1 :]:
        cells = {_column_name(cell.get("r", "")): cell for cell in row.findall("x:c", NS)}
        lat_cell = cells.get(lat_column)
        lng_cell = cells.get(lng_column)
        if lat_cell is None or lng_cell is None:
            continue
        lat_text = _cell_text(lat_cell, shared)
        lng_text = _cell_text(lng_cell, shared)
        try:
            source_lat = float(lat_text)  # type: ignore[arg-type]
            source_lng = float(lng_text)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        target_lat, target_lng, iterations, residual_m = gcj02_to_cgcs2000(source_lat, source_lng)
        for cell, number in ((lat_cell, target_lat), (lng_cell, target_lng)):
            cell.attrib.pop("t", None)
            value = cell.find("x:v", NS)
            if value is None:
                value = ET.SubElement(cell, f"{{{MAIN_NS}}}v")
            value.text = f"{number:.9f}"
        converted.append(
            {
                "row": int(row.get("r", "0")),
                "source_lat": source_lat,
                "source_lng": source_lng,
                "target_lat": target_lat,
                "target_lng": target_lng,
                "iterations": iterations,
                "residual_m": residual_m,
            }
        )
    if not converted:
        return xml_data, []
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), converted


def convert_workbook(source: Path, destination: Path) -> list[dict[str, float | int]]:
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination must be different files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as input_xlsx:
        shared = _shared_strings(input_xlsx)
        sheet_paths = list(dict.fromkeys(_worksheet_paths(input_xlsx)))
        replacements = {}
        converted = []
        for sheet_path in sheet_paths:
            updated_xml, sheet_results = _convert_sheet(input_xlsx.read(sheet_path), shared)
            replacements[sheet_path] = updated_xml
            converted.extend(sheet_results)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", dir=destination.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with zipfile.ZipFile(temporary_path, "w") as output_xlsx:
                for item in input_xlsx.infolist():
                    output_xlsx.writestr(item, replacements.get(item.filename, input_xlsx.read(item.filename)))
            shutil.move(temporary_path, destination)
            os.chmod(destination, source.stat().st_mode & 0o777)
        finally:
            temporary_path.unlink(missing_ok=True)
    return converted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    results = convert_workbook(args.source, args.destination)
    if not results:
        raise SystemExit("No worksheets containing numeric lat/lng coordinate pairs were found")
    print(f"Converted {len(results)} coordinate pair(s):")
    for result in results:
        print(
            "row {row}: ({source_lat:.9f}, {source_lng:.9f}) -> "
            "({target_lat:.9f}, {target_lng:.9f}); "
            "iterations={iterations}, closure_residual={residual_m:.6g} m".format(**result)
        )


if __name__ == "__main__":
    main()
