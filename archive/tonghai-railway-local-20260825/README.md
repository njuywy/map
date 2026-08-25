# 通海铁路本地应用快照（2026-08-25）

这是整合进 `my-blog` 前保留的完整本地版本，源目录 `/home/ywy/dev/_src/location` 未被删除或移动。

## 运行交互地图

```bash
cd interactive-map
./start_map.sh
```

## 刷新 CGCS2000 点位

在本目录执行：

```bash
python3 update_interactive_map_points.py CGCS2000经纬度.xlsx
```

快照包含坐标工作簿、转换与地图生成脚本、交互地图、测试、GeoJSON 和静态 PNG。原目录中没有可归档的静态 PDF。
