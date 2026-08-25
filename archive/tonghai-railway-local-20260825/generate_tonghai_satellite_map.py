#!/usr/bin/env python3
"""Generate a Tianditu satellite map of the Tonghai port railway and a point.

Requires Pillow and a browser-type Tianditu token supplied through the
TIANDITU_TOKEN environment variable.  Railway geometry is read from the
OpenStreetMap Overpass API and checked by name before it is drawn.
"""

from __future__ import annotations

import io
import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


POINT_LAT = 31.832086581
POINT_LON = 121.077742102
ROUTE_NAME = "通海港区铁路专用线"
OUTPUT_PNG = Path("南通港通海港区至通州湾港区铁路专用线_点位卫星图.png")
OUTPUT_PDF = Path("南通港通海港区至通州湾港区铁路专用线_点位卫星图.pdf")
OUTPUT_GEOJSON = Path("通海铁路专用线_点位标注.geojson")
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
TILE_SIZE = 256
USER_AGENT = "Tonghai-railway-map/1.0 (local cartographic output)"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def overpass_route() -> list[dict]:
    query = (
        '[out:json][timeout:60];'
        'way["railway"]["name"="通海港区铁路专用线"]'
        '(31.78,121.02,31.96,121.21);out tags geom;'
    )
    data = urllib.parse.urlencode({"data": query}).encode()
    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=data,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        elements = json.load(response).get("elements", [])
    ways = [element for element in elements if element.get("geometry")]
    if not ways:
        raise RuntimeError(f"No OpenStreetMap railway geometry found for {ROUTE_NAME}")
    return ways


def world_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    scale = TILE_SIZE * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(max(-85.05112878, min(85.05112878, lat))))
    y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * scale
    return x, y


def lonlat_from_world_pixel(x: float, y: float, zoom: int) -> tuple[float, float]:
    scale = TILE_SIZE * (2**zoom)
    lon = x / scale * 360.0 - 180.0
    mercator_y = math.pi * (1.0 - 2.0 * y / scale)
    lat = math.degrees(math.atan(math.sinh(mercator_y)))
    return lon, lat


def tile_url(layer: str, zoom: int, x: int, y: int, token: str, host: int) -> str:
    query = urllib.parse.urlencode(
        {
            "SERVICE": "WMTS",
            "REQUEST": "GetTile",
            "VERSION": "1.0.0",
            "LAYER": layer,
            "STYLE": "default",
            "TILEMATRIXSET": "w",
            "FORMAT": "tiles",
            "TILEMATRIX": zoom,
            "TILEROW": y,
            "TILECOL": x,
            "tk": token,
        }
    )
    return f"https://t{host}.tianditu.gov.cn/{layer}_w/wmts?{query}"


def get_tile(layer: str, zoom: int, x: int, y: int, token: str) -> Image.Image:
    cache = Path("/tmp/tianditu_tonghai_tiles") / layer / str(zoom) / str(x)
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / f"{y}.tile"
    if cache_file.exists():
        try:
            return Image.open(cache_file).convert("RGBA")
        except Exception:
            cache_file.unlink(missing_ok=True)
    last_error = None
    for attempt in range(4):
        host = (x + y + attempt) % 8
        request = urllib.request.Request(
            tile_url(layer, zoom, x, y, token, host),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://map.tianditu.gov.cn/",
                "Origin": "https://map.tianditu.gov.cn",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                content = response.read()
            tile = Image.open(io.BytesIO(content)).convert("RGBA")
            cache_file.write_bytes(content)
            return tile
        except Exception as error:
            last_error = error
            time.sleep(0.4 * (attempt + 1))
    if layer == "cia":
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    raise RuntimeError(f"Unable to download Tianditu tile {layer}/{zoom}/{x}/{y}: {last_error}")


class MapImage:
    def __init__(
        self,
        image: Image.Image,
        zoom: int,
        left_world_px: float,
        top_world_px: float,
        source_width: float,
        source_height: float,
    ) -> None:
        self.image = image
        self.zoom = zoom
        self.left_world_px = left_world_px
        self.top_world_px = top_world_px
        self.source_width = source_width
        self.source_height = source_height

    def point(self, lon: float, lat: float) -> tuple[float, float]:
        x, y = world_pixel(lon, lat, self.zoom)
        return (
            (x - self.left_world_px) / self.source_width * self.image.width,
            (y - self.top_world_px) / self.source_height * self.image.height,
        )


def render_map(
    bbox: tuple[float, float, float, float],
    zoom: int,
    size: tuple[int, int],
    token: str,
) -> MapImage:
    west, south, east, north = bbox
    left, top = world_pixel(west, north, zoom)
    right, bottom = world_pixel(east, south, zoom)
    tile_left = math.floor(left / TILE_SIZE)
    tile_top = math.floor(top / TILE_SIZE)
    tile_right = math.floor((right - 1) / TILE_SIZE)
    tile_bottom = math.floor((bottom - 1) / TILE_SIZE)
    mosaic = Image.new(
        "RGBA",
        ((tile_right - tile_left + 1) * TILE_SIZE, (tile_bottom - tile_top + 1) * TILE_SIZE),
    )
    for tile_y in range(tile_top, tile_bottom + 1):
        for tile_x in range(tile_left, tile_right + 1):
            position = ((tile_x - tile_left) * TILE_SIZE, (tile_y - tile_top) * TILE_SIZE)
            mosaic.alpha_composite(get_tile("img", zoom, tile_x, tile_y, token), position)
            mosaic.alpha_composite(get_tile("cia", zoom, tile_x, tile_y, token), position)
    crop_box = (
        round(left - tile_left * TILE_SIZE),
        round(top - tile_top * TILE_SIZE),
        round(right - tile_left * TILE_SIZE),
        round(bottom - tile_top * TILE_SIZE),
    )
    cropped = mosaic.crop(crop_box).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    return MapImage(cropped, zoom, left, top, right - left, bottom - top)


def route_points(map_image: MapImage, ways: list[dict]) -> list[list[tuple[float, float]]]:
    return [
        [map_image.point(vertex["lon"], vertex["lat"]) for vertex in way["geometry"]]
        for way in ways
    ]


def draw_route(draw: ImageDraw.ImageDraw, paths: list[list[tuple[float, float]]], scale: float = 1.0) -> None:
    for path in paths:
        draw.line(path, fill=(20, 20, 20), width=max(4, round(13 * scale)), joint="curve")
        draw.line(path, fill=(255, 210, 0), width=max(2, round(7 * scale)), joint="curve")


def draw_marker(draw: ImageDraw.ImageDraw, x: float, y: float, radius: int = 18) -> None:
    draw.ellipse((x - radius - 5, y - radius - 5, x + radius + 5, y + radius + 5), fill=(255, 255, 255, 230))
    draw.polygon(((x, y + radius * 1.9), (x - radius * 0.72, y + radius * 0.25), (x + radius * 0.72, y + radius * 0.25)), fill=(219, 37, 48))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(219, 37, 48), outline="white", width=3)
    draw.ellipse((x - radius * 0.34, y - radius * 0.34, x + radius * 0.34, y + radius * 0.34), fill="white")


def label_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    anchor: str = "la",
    fill: tuple[int, int, int] = (255, 255, 255),
) -> None:
    x, y = xy
    box = draw.textbbox((x, y), text, font=text_font, anchor=anchor, stroke_width=1)
    padded = (box[0] - 8, box[1] - 5, box[2] + 8, box[3] + 5)
    draw.rounded_rectangle(padded, radius=8, fill=(15, 25, 30, 190), outline=(255, 255, 255, 210), width=1)
    draw.text((x, y), text, font=text_font, anchor=anchor, fill=fill, stroke_width=1, stroke_fill=(0, 0, 0))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and draw.textlength(candidate, font=text_font) > max_width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def haversine(a: dict, b: dict) -> float:
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def route_length(ways: list[dict]) -> float:
    return sum(
        haversine(a, b)
        for way in ways
        for a, b in zip(way["geometry"], way["geometry"][1:])
    )


def point_route_distance(ways: list[dict]) -> float:
    cos_lat = math.cos(math.radians(POINT_LAT))

    def local(vertex: dict) -> tuple[float, float]:
        return (
            (vertex["lon"] - POINT_LON) * 111320.0 * cos_lat,
            (vertex["lat"] - POINT_LAT) * 110574.0,
        )

    best = float("inf")
    for way in ways:
        for first, second in zip(way["geometry"], way["geometry"][1:]):
            ax, ay = local(first)
            bx, by = local(second)
            dx, dy = bx - ax, by - ay
            denominator = dx * dx + dy * dy
            t = max(0.0, min(1.0, -(ax * dx + ay * dy) / denominator)) if denominator else 0.0
            best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def draw_scale_bar(draw: ImageDraw.ImageDraw, bbox: tuple[float, float, float, float], width: int, height: int) -> None:
    west, south, east, north = bbox
    metres = 5000
    degree_width = metres / (111320.0 * math.cos(math.radians((south + north) / 2)))
    pixel_width = degree_width / (east - west) * width
    x0, y0 = 55, height - 64
    draw.rectangle((x0 - 18, y0 - 46, x0 + pixel_width + 18, y0 + 26), fill=(0, 0, 0, 150))
    draw.line((x0, y0, x0 + pixel_width, y0), fill="white", width=5)
    for x in (x0, x0 + pixel_width / 2, x0 + pixel_width):
        draw.line((x, y0 - 11, x, y0 + 11), fill="white", width=4)
    draw.text((x0, y0 - 18), "0", font=font(23, True), anchor="mb", fill="white")
    draw.text((x0 + pixel_width / 2, y0 - 18), "2.5", font=font(23, True), anchor="mb", fill="white")
    draw.text((x0 + pixel_width, y0 - 18), "5 km", font=font(23, True), anchor="mb", fill="white")


def draw_north_arrow(draw: ImageDraw.ImageDraw, width: int) -> None:
    x, y = width - 70, 90
    draw.ellipse((x - 42, y - 52, x + 42, y + 54), fill=(0, 0, 0, 145), outline="white", width=2)
    draw.polygon(((x, y - 38), (x - 17, y + 19), (x, y + 8), (x + 17, y + 19)), fill="white")
    draw.text((x, y + 27), "N", font=font(25, True), anchor="mm", fill="white")


def create_geojson(ways: list[dict]) -> None:
    features = []
    for way in ways:
        features.append(
            {
                "type": "Feature",
                "properties": {"name": ROUTE_NAME, "osm_way_id": way["id"], "source": "OpenStreetMap"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[p["lon"], p["lat"]] for p in way["geometry"]],
                },
            }
        )
    features.append(
        {
            "type": "Feature",
            "properties": {"name": "转换点位", "crs": "CGCS2000 / EPSG:4490"},
            "geometry": {"type": "Point", "coordinates": [POINT_LON, POINT_LAT]},
        }
    )
    OUTPUT_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    token = os.environ.get("TIANDITU_TOKEN")
    if not token:
        raise SystemExit("Set TIANDITU_TOKEN to a valid browser-type Tianditu token")

    ways = overpass_route()
    route_km = route_length(ways) / 1000.0
    nearest_m = point_route_distance(ways)
    create_geojson(ways)

    canvas = Image.new("RGB", (2800, 1980), (241, 244, 246))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 2800, 162), fill=(13, 39, 54))
    draw.text((65, 63), "南通港通海港区至通州湾港区铁路专用线（一期）卫星图", font=font(52, True), fill="white", anchor="lm")
    draw.text((66, 125), "CGCS2000 点位标注 · 天地图影像底图", font=font(28), fill=(183, 216, 229), anchor="lm")

    main_box = (60, 190, 1820, 1880)
    main_bbox = (121.006, 31.774, 121.220, 31.954)
    main_map = render_map(main_bbox, 14, (main_box[2] - main_box[0], main_box[3] - main_box[1]), token)
    main_draw = ImageDraw.Draw(main_map.image, "RGBA")
    draw_route(main_draw, route_points(main_map, ways), 1.0)

    stations = [
        (121.1783968, 31.9278785, "海门站"),
        (121.0504339, 31.8143874, "通海港站"),
    ]
    for lon, lat, name in stations:
        sx, sy = main_map.point(lon, lat)
        main_draw.rounded_rectangle((sx - 10, sy - 10, sx + 10, sy + 10), radius=3, fill=(0, 212, 255), outline="white", width=3)
        label_box(main_draw, (sx + 18, sy), name, font(25, True), "lm", (155, 240, 255))
    point_x, point_y = main_map.point(POINT_LON, POINT_LAT)
    draw_marker(main_draw, point_x, point_y, 23)
    label_box(main_draw, (point_x + 34, point_y - 20), "目标点位", font(27, True), "ls", (255, 230, 120))
    label_box(main_draw, main_map.point(121.096, 31.887), "通海港区铁路专用线", font(28, True), "mm", (255, 224, 63))
    draw_scale_bar(main_draw, main_bbox, main_map.image.width, main_map.image.height)
    draw_north_arrow(main_draw, main_map.image.width)
    canvas.paste(main_map.image, main_box[:2])
    draw.rectangle(main_box, outline=(255, 255, 255), width=3)

    side_x, side_y, side_w = 1860, 190, 880
    draw.rounded_rectangle((side_x, side_y, side_x + side_w, 1880), radius=18, fill="white", outline=(195, 205, 210), width=2)
    draw.text((side_x + 35, side_y + 52), "点位局部放大", font=font(36, True), fill=(18, 51, 68), anchor="lm")
    draw.text((side_x + 35, side_y + 95), "约 1 米/像素，十字线交点为目标坐标", font=font(23), fill=(82, 101, 111), anchor="lm")

    inset_size = (810, 720)
    half_pixels = 405
    center_x, center_y = world_pixel(POINT_LON, POINT_LAT, 17)
    west, north = lonlat_from_world_pixel(center_x - half_pixels, center_y - 360, 17)
    east, south = lonlat_from_world_pixel(center_x + half_pixels, center_y + 360, 17)
    inset_map = render_map((west, south, east, north), 17, inset_size, token)
    inset_draw = ImageDraw.Draw(inset_map.image, "RGBA")
    draw_route(inset_draw, route_points(inset_map, ways), 0.75)
    ix, iy = inset_map.point(POINT_LON, POINT_LAT)
    inset_draw.line((ix - 80, iy, ix + 80, iy), fill=(255, 255, 255, 220), width=3)
    inset_draw.line((ix, iy - 80, ix, iy + 80), fill=(255, 255, 255, 220), width=3)
    inset_draw.ellipse((ix - 33, iy - 33, ix + 33, iy + 33), outline=(219, 37, 48), width=8)
    draw_marker(inset_draw, ix, iy, 16)
    inset_pos = (side_x + 35, side_y + 125)
    canvas.paste(inset_map.image, inset_pos)
    draw.rectangle((inset_pos[0], inset_pos[1], inset_pos[0] + inset_size[0], inset_pos[1] + inset_size[1]), outline=(13, 39, 54), width=3)

    info_top = side_y + 885
    draw.text((side_x + 35, info_top), "图例与点位信息", font=font(34, True), fill=(18, 51, 68), anchor="la")
    legend_y = info_top + 65
    draw.line((side_x + 45, legend_y, side_x + 135, legend_y), fill=(20, 20, 20), width=14)
    draw.line((side_x + 45, legend_y, side_x + 135, legend_y), fill=(255, 210, 0), width=7)
    draw.text((side_x + 160, legend_y), "铁路专用线公开线位", font=font(26), fill=(30, 42, 48), anchor="lm")
    draw_marker(draw, side_x + 88, legend_y + 65, 14)
    draw.text((side_x + 160, legend_y + 66), "转换后的 CGCS2000 点位", font=font(26), fill=(30, 42, 48), anchor="lm")

    lines = [
        f"纬度：{POINT_LAT:.9f}°",
        f"经度：{POINT_LON:.9f}°",
        f"与公开线路中心线最近距离：约 {nearest_m:.1f} m",
        f"公开线路几何长度：约 {route_km:.2f} km",
        "官方验收长度：24.481 km",
        "起讫：海门站—通海港站",
        "坐标参考系：CGCS2000（EPSG:4490）",
    ]
    text_y = legend_y + 135
    for index, line in enumerate(lines):
        color = (188, 43, 54) if index == 2 else (45, 58, 65)
        draw.text((side_x + 45, text_y), line, font=font(25, index == 2), fill=color, anchor="la")
        text_y += 48

    note_box = (side_x + 35, text_y + 12, side_x + side_w - 35, text_y + 190)
    draw.rounded_rectangle(note_box, radius=12, fill=(244, 247, 249), outline=(205, 214, 219), width=2)
    note = "说明：线路来自 OpenStreetMap 公开数据，并以工程验收资料核对名称、起讫和长度；最近距离仅作地图核验，不替代测量放样。"
    note_font = font(23)
    wrapped_note = wrap_text(draw, note, note_font, note_box[2] - note_box[0] - 40)
    draw.multiline_text((note_box[0] + 20, note_box[1] + 20), wrapped_note, font=note_font, fill=(74, 88, 96), spacing=10)

    footer_y = 1905
    draw.text((60, footer_y), "底图：天地图影像及影像注记（访问日期 2026-08-25）", font=font(21), fill=(80, 94, 101), anchor="la")
    draw.text((1380, footer_y), "线路：© OpenStreetMap contributors  |  工程依据：2023年竣工环保验收调查报告", font=font(21), fill=(80, 94, 101), anchor="ma")
    draw.text((2740, footer_y), "制图日期：2026-08-25", font=font(21), fill=(80, 94, 101), anchor="ra")

    canvas.save(OUTPUT_PNG, optimize=True)
    canvas.save(OUTPUT_PDF, "PDF", resolution=200.0, quality=95)
    print(f"Created {OUTPUT_PNG} ({canvas.width}x{canvas.height})")
    print(f"Created {OUTPUT_PDF}")
    print(f"Created {OUTPUT_GEOJSON}")
    print(f"OSM route length: {route_km:.3f} km; point-to-route distance: {nearest_m:.3f} m")


if __name__ == "__main__":
    main()
