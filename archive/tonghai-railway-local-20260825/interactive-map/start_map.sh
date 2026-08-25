#!/usr/bin/env bash
set -euo pipefail

map_dir="$(cd "$(dirname "$0")" && pwd)"
map_port="${1:-8088}"
requested_port="$map_port"

if [[ ! "$map_port" =~ ^[0-9]+$ ]] || (( map_port < 1 || map_port > 65535 )); then
  echo "错误：端口必须是 1 到 65535 之间的整数。" >&2
  exit 2
fi

while ! python3 - "$map_port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    try:
        server.bind(("127.0.0.1", port))
    except OSError:
        raise SystemExit(1)
PY
do
  ((map_port += 1))
  if (( map_port > 65535 )); then
    echo "错误：未找到可用端口。" >&2
    exit 1
  fi
done

if [[ "$map_port" != "$requested_port" ]]; then
  echo "端口 $requested_port 已被占用，自动改用 $map_port。"
fi
map_url="http://127.0.0.1:${map_port}/"

cd "$map_dir"
if [[ "${MAP_SKIP_BROWSER:-0}" != "1" ]] && command -v xdg-open >/dev/null 2>&1; then
  (sleep 1; xdg-open "$map_url" >/dev/null 2>&1 || true) &
fi

echo "交互式地图已启动：$map_url"
echo "按 Ctrl+C 停止服务。"
exec python3 -m http.server "$map_port" --bind 127.0.0.1
