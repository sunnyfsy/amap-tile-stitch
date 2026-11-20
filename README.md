# amap-tile-stitch（高德地图瓦片拼接）

按经纬度矩形框 + zoom 级别批量下载高德公开瓦片，并拼接为一张完整高清大图。相比浏览器逐屏截图，不触发登录/滑块验证、无需手动拖拽、瓦片自动缓存可复用。

> 这是一个 [WorkBuddy](https://www.workbuddy.cn/) Skill。放入技能的 `skills/` 目录后即可通过自然语言触发使用。

## 功能特性

- **两种底图**：标准路网图（含道路与 POI 名称）、卫星影像（`--satellite`）
- **缩放级别**：z12–z18，覆盖从区域概览到建筑细节
- **瓦片缓存**：自动缓存到输出目录旁 `_tiles/z<zoom>/`，重复运行或调整边界只补下载新增瓦片
- **格式选择**：PNG 无损 / JPG 压缩（q90），可选 USM 锐化（`--sharpen`）
- **并发下载**：默认 12 线程，可配置

## 目录结构

```
amap-tile-stitch/
├── SKILL.md                         # 技能主说明（触发条件与工作流）
├── references/
│   └── zoom-region-guide.md         # zoom 对照表、瓦片数量估算、区域边界参考
└── scripts/
    └── stitch_amap.py               # 下载+拼接脚本
```

## 快速开始

依赖：Python 3 + Pillow（`pip install Pillow`）

```bash
python scripts/stitch_amap.py \
  --west 104.07 --east 104.21 --south 30.62 --north 30.74 \
  --zoom 17 --out "C:/Users/Administrator/Desktop/chenghua.png" \
  --workers 12 --sharpen
```

卫星影像：

```bash
python scripts/stitch_amap.py \
  --west 104.07 --east 104.21 --south 30.62 --north 30.74 \
  --zoom 18 --out "chenghua_satellite.jpg" --satellite
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `--west/--east/--south/--north` | 矩形四角经纬度（GCJ 近似即可），需满足 west<east、south<north |
| `--zoom` | 缩放级别 10–18，z18 为公开瓦片上限（z19 返回空白，勿用） |
| `--out` | 输出路径，`.png` 无损 / `.jpg/.jpeg` 压缩 |
| `--satellite` | 卫星影像模式（默认路网图） |
| `--workers` | 并发数，默认 12，z18 大范围勿超过 16 |
| `--jpeg-quality` | JPEG 质量，默认 90 |
| `--sharpen` | 拼接后轻度 USM 锐化，适合 PNG + 细节核对 |

## zoom 对照（成都纬度经验值）

| zoom | 比例尺 | 每像素地面距离 | 适用场景 |
|---|---|---|---|
| 12 | ~10 km | ~33 m/px | 市域概览 |
| 13 | ~2 km | ~16.7 m/px | 全区轮廓 |
| 14 | ~1 km | ~8.4 m/px | 区级概览 |
| 15 | ~200 m | ~4.2 m/px | 一般区级图 |
| 16 | ~100 m | ~2.1 m/px | 较细细节 |
| 17 | ~50 m | ~1.05 m/px | 建筑细节（常用高清） |
| 18 | ~25 m | ~0.52 m/px | 最高清（网页版上限） |

更多区域边界参考与常见问题见 [`references/zoom-region-guide.md`](references/zoom-region-guide.md)。

## 约束

- 仅用于区域概览/细节图导出，不做大批量违规爬取
- 产出为严格矩形覆盖图，不沿行政边界裁切（如需贴合边界请另接 GeoJSON 掩膜）
- 瓦片服务为高德公开接口，请合理使用

## License

个人使用。
