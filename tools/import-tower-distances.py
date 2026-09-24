#!/usr/bin/env python3
"""Import tower distances from XLS, matching point numbers and existing coordinates.

Install the reader with: python3 -m pip install -r tools/requirements-map.txt
"""

import argparse
import json
import math
from pathlib import Path

import xlrd


PREFIX = "window.MAP_DATA = "


def read_distances(workbook):
    records = {}
    for sheet in xlrd.open_workbook(workbook).sheets():
        if not sheet.nrows:
            continue
        headers = [str(value).strip() for value in sheet.row_values(0)]
        if "最近铁塔距离（米）" not in headers:
            continue
        columns = [headers.index(name) for name in ("序号", "经度", "纬度", "最近铁塔距离（米）")]
        for row in range(1, sheet.nrows):
            number, first, second, distance = [sheet.cell_value(row, column) for column in columns]
            if number == "" or number in ("300米以内", "200米以内", "100米以内"):
                continue
            try:
                number, first, second, distance = map(float, (number, first, second, distance))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{sheet.name} 第 {row + 1} 行不是有效点位数据") from error
            if not all(map(math.isfinite, (number, first, second, distance))) or distance < 0 or number < 1 or not number.is_integer():
                raise ValueError(f"{sheet.name} 第 {row + 1} 行的序号或距离无效")
            number = int(number)
            if number in records:
                raise ValueError(f"点位 {number} 重复")
            records[number] = (first, second, distance)
    if not records:
        raise ValueError("表格中没有找到点位距离")
    return records


def update_distances(data, records):
    points = [feature for feature in data["features"] if feature["geometry"]["type"] == "Point"]
    numbers = [point["properties"]["point_number"] for point in points]
    if len(set(numbers)) != len(numbers) or set(numbers) != set(records):
        raise ValueError("表格序号与地图点位不完全对应，请检查缺失或重复的点位")
    for point in points:
        number = point["properties"]["point_number"]
        first, second, distance = records[number]
        longitude, latitude = point["geometry"]["coordinates"]
        # The supplied workbook has longitude/latitude headings reversed.
        if not any(abs(longitude - lng) < 1e-8 and abs(latitude - lat) < 1e-8
                   for lng, lat in ((first, second), (second, first))):
            raise ValueError(f"点位 {number} 的坐标与地图不一致")
        point["properties"]["tower_distance_m"] = distance
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--map-data", type=Path, nargs="+", default=[Path(__file__).resolve().parents[1] / "source/map-data.js"])
    parser.add_argument("--geojson", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    records = read_distances(args.workbook)
    outputs = []
    for path in args.map_data + args.geojson:
        source = path.read_text(encoding="utf-8").strip()
        is_script = path in args.map_data
        if is_script:
            if not source.startswith(PREFIX) or not source.endswith(";"):
                raise ValueError(f"不支持的地图数据格式：{path}")
            source = source[len(PREFIX):-1]
        data = update_distances(json.loads(source), records)
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        outputs.append((path, f"{PREFIX}{serialized};\n" if is_script else f"{serialized}\n"))
    # Validate every target before writing any output.
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
        print(f"已更新 {len(records)} 个点位距离：{path}")


if __name__ == "__main__":
    main()
