#!/usr/bin/env python3
"""
amap-tile-stitch: 下载高德地图公开瓦片并拼接为一张完整大图。

用法示例:
  python stitch_amap.py --west 104.07 --east 104.21 --south 30.62 --north 30.74 \
      --zoom 17 --out "C:/Users/Administrator/Desktop/chenghua.png"
  python stitch_amap.py --west 104.07 --east 104.21 --south 30.62 --north 30.74 \
      --zoom 18 --out "chenghua.jpg" --satellite --workers 12

边界填 WGS84/GCJ 近似经纬度即可，瓦片误差在使用容限内。
"""
import argparse
import math
import os
import sys
import io
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageFilter

# 大图防 DecompressionBombError
Image.MAX_IMAGE_PIXELS = None

SUBDOMAINS = ["1", "2", "3", "4"]

# 路网瓦片（含道路、POI 名称、小区轮廓）
ROADNET_URL = (
    "https://webrd0{s}.is.autonavi.com/appmaptile"
    "?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
)
# 卫星影像瓦片
SATELLITE_URL = (
    "https://webst0{s}.is.autonavi.com/appmaptile"
    "?style=6&x={x}&y={y}&z={z}"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://ditu.amap.com/",
}


def deg2num(lat_deg, lon_deg, zoom):
    """WGS/GCJ 经纬度 -> Web 墨卡托瓦片 x,y（0,0 为左上）。"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def _is_valid_tile(data):
    """校验返回内容是合法 256x256 瓦片；空白纯色瓦片字节数很小也应接受。"""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im.size == (256, 256)
    except Exception:
        return False


def fetch_tile(x, y, zoom, tiles_dir, satellite):
    """返回 (x, y, 本地路径或 None)。已缓存直接命中。"""
    ext = "png"
    path = os.path.join(tiles_dir, f"z{zoom}_{x}_{y}.{ext}")
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return x, y, path

    url_template = SATELLITE_URL if satellite else ROADNET_URL
    for s in SUBDOMAINS:
        url = url_template.format(s=s, x=x, y=y, z=zoom)
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                if _is_valid_tile(data):
                    with open(path, "wb") as f:
                        f.write(data)
                    return x, y, path
            except Exception:
                continue
    return x, y, None


def main():
    ap = argparse.ArgumentParser(description="高德瓦片下载拼接")
    ap.add_argument("--west", type=float, required=True, help="西边界经度")
    ap.add_argument("--east", type=float, required=True, help="东边界经度")
    ap.add_argument("--south", type=float, required=True, help="南边界纬度")
    ap.add_argument("--north", type=float, required=True, help="北边界纬度")
    ap.add_argument("--zoom", type=int, required=True, help="缩放级别 10-18")
    ap.add_argument("--out", type=str, required=True, help="输出图片路径 .png/.jpg/.jpeg")
    ap.add_argument("--tiles-dir", type=str, default=None, help="瓦片缓存目录，默认输出旁 _tiles 子目录")
    ap.add_argument("--workers", type=int, default=12, help="并发下载数，默认 12")
    ap.add_argument("--satellite", action="store_true", help="使用卫星影像瓦片（默认路网图）")
    ap.add_argument("--jpeg-quality", type=int, default=90, help="JPEG 质量 0-100，默认 90")
    ap.add_argument("--sharpen", action="store_true", help="拼接后做轻度 USM 锐化，补偿位图瓦片文字/线条发虚")
    args = ap.parse_args()

    if not (args.west < args.east and args.south < args.north):
        ap.error("经纬度范围顺序错误：需满足 west<east 且 south<north")
    if not (10 <= args.zoom <= 18):
        ap.error("zoom 仅支持 10-18")

    x0, y0 = deg2num(args.north, args.west, args.zoom)   # 左上
    x1, y1 = deg2num(args.south, args.east, args.zoom)   # 右下
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    total = nx * ny

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    tiles_dir = args.tiles_dir or os.path.join(out_dir, "_tiles", f"z{args.zoom}")
    os.makedirs(tiles_dir, exist_ok=True)

    print(f"[范围] 经度 {args.west}~{args.east}, 纬度 {args.south}~{args.north}")
    print(f"[级别] zoom={args.zoom} | 瓦片 {nx}x{ny}={total} | 输出像素 {nx*256}x{ny*256}")
    print(f"[缓存] {tiles_dir}")

    tasks = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(lambda p: fetch_tile(p[0], p[1], args.zoom, tiles_dir, args.satellite), tasks):
            results.append(r)
            done += 1
            if done % 200 == 0 or done == total:
                print(f"  进度 {done}/{total}")

    ok = sum(1 for _, _, p in results if p)
    failed = total - ok
    print(f"[下载] 成功 {ok}, 失败 {failed}")

    # 拼接
    T = 256
    fill_color = (0, 0, 0) if args.satellite else (255, 255, 255)
    canvas = Image.new("RGB", (nx * T, ny * T), fill_color)
    for x, y, path in results:
        if path:
            tile = Image.open(path).convert("RGB")
            canvas.paste(tile, ((x - x0) * T, (y - y0) * T))

    # 轻度 USM 锐化：路网瓦片是位图，文字/线条经锐化后更实
    if args.sharpen:
        canvas = canvas.filter(
            ImageFilter.UnsharpMask(radius=1.4, percent=90, threshold=2)
        )
        print("[处理] 已应用 USM 锐化")

    out_abs = os.path.abspath(args.out)
    ext = os.path.splitext(out_abs)[1].lower()
    if ext in (".jpg", ".jpeg"):
        canvas.save(out_abs, "JPEG", quality=args.jpeg_quality, optimize=True)
    else:
        canvas.save(out_abs, "PNG", optimize=True)

    size_mb = os.path.getsize(out_abs) / 1024 / 1024
    print(f"[完成] {out_abs}")
    print(f"[尺寸] {canvas.width}x{canvas.height} px | {size_mb:.1f} MB")
    if failed:
        print(f"[提示] {failed} 张瓦片缺失，对应位置为填充底色；如多为黑/白块可重跑（缓存会跳过已下载瓦片）。")


if __name__ == "__main__":
    main()
