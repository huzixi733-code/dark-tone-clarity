# 暗调清晰质感 · Dark Tone Clarity

一个 [WorkBuddy](https://www.workbuddy.cn) 调色技能（skill），把照片一键处理成
**压暗曝光 + 强中间调对比 + 去饱和 + 微微偏冷 + 局部质感 + 锐化** 的电影感暗调风格。

适用于人像、产品、静物等题材：暗部干净不脏、材质纹理突出、色彩克制。

> 核心是一个固化好的调色脚本，默认套用一组预设参数，做到「给图即出片」。

## ✨ 效果参数（默认配方）

| 参数 | 值 | 作用 |
|------|-----|------|
| 曝光 exposure | -23 | 整体亮度 ×≈0.78 |
| 鲜明度 vibrance | -48 | 选择性去饱和（保中性灰/肤色） |
| 高光 highlights | +34 | 提亮亮部、保留高光细节 |
| 阴影 shadows | -16 | 压暗暗部 |
| 对比度 contrast | +42 | S 型拉伸 |
| 黑点 blacks | +10 | 微抬纯黑，胶片感 |
| 饱和度 saturation | -25 | 全局去饱和 |
| 色温 temperature | -10 | 微微偏冷 |
| 清晰度 clarity | +65 | 局部对比（质感核心） |
| 锐度 sharpness | +35 | 边缘锐化（USM） |

## 🚀 在 WorkBuddy 中使用

1. 把本仓库内容放入 `~/.workbuddy/skills/dark-tone-clarity/`（保留 `SKILL.md` 与 `scripts/`、`references/` 结构）。
2. 新会话中直接发一张图片，并说「暗调清晰质感」「电影感暗调」等，即可自动出图。
3. 可调强度：`--intensity 0.6`；可逐参数覆盖：`--exposure -30 --clarity 80`。

## 🛠 命令行直接调用

```bash
pip install Pillow numpy
python scripts/apply_style.py photo.jpg            # 输出 photo_darktone.jpg
python scripts/apply_style.py photo.jpg --intensity 0.6
python scripts/apply_style.py photo.jpg --show-params
```

完整参数映射与调参方向见 [`references/preset.md`](references/preset.md)，技能说明见 [`SKILL.md`](SKILL.md)。

## 📦 目录结构

```
dark-tone-clarity/
├── SKILL.md              # 技能定义与触发说明
├── scripts/
│   └── apply_style.py    # 调色脚本（Pillow + numpy）
└── references/
    └── preset.md         # 参数表与映射逻辑
```

## ⚠️ 说明

- 本技能做「风格化调色」，不做抠图、磨皮或换背景等复杂编辑。
- 依赖：Python + Pillow + numpy。
