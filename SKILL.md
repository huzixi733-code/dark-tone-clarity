---
name: dark-tone-clarity
description: 把照片一键调成「暗调清晰质感」风格——压暗曝光、强中间调对比、去饱和、微微偏冷、局部对比（清晰度）与锐化，呈现电影感暗调。当用户提供图片并提到“暗调”“清晰质感”“电影感暗调”“暗调清晰质感”或想要压暗+锐利+克制色彩的人像/产品/静物效果时使用。依赖 Pillow 与 numpy。
agent_created: true
---

# 暗调清晰质感 (Dark Tone · Clarity)

把任意照片处理成「压暗 + 强对比 + 去饱和 + 微偏冷 + 局部质感 + 锐化」的电影感暗调风格。
核心是一个固化好的调色脚本，默认套用一组预设参数，做到「给图即出片」。

适用题材：人像、产品、静物为主（默认参数已针对这类题材做了平衡，暗部不脏、材质突出）。

## 何时使用

- 用户发来一张图片，并说要「暗调清晰质感」「电影感暗调」「高级灰暗调」等。
- 用户想要：压暗但保留细节、提升质感与锐度、色彩更克制冷调。
- 用户明确要求用本 skill 出图。

## 快速上手

1. 确认图片路径（用户上传或指定的文件）。
2. 用 Python 运行本 skill 的脚本 `scripts/apply_style.py`，默认即应用全套预设：

   ```bash
   python <skill_dir>/scripts/apply_style.py "<图片路径>"
   ```

   脚本会自动输出 `<原名>_darktone.<ext>`，并尊重 EXIF 拍摄方向、保留透明通道。

3. 若运行环境缺少依赖，先安装：

   ```bash
   pip install Pillow numpy
   ```

4. 把生成的 `_darktone` 文件通过 `present_files` 交给用户查看。

## 调整与覆盖

脚本默认套用预设；如需微调，可用命令行参数逐个覆盖（量纲均为 -100~+100）：

```bash
python <skill_dir>/scripts/apply_style.py photo.jpg --exposure -30 --clarity 80
python <skill_dir>/scripts/apply_style.py photo.jpg --intensity 0.6   # 整体强度 0~1
python <skill_dir>/scripts/apply_style.py photo.jpg --show-params     # 打印生效参数
```

可调参数：`--exposure --vibrance --highlights --shadows --contrast --blacks --saturation --temperature --sharpness --clarity`。

实用建议：
- 想更暗更狠：调低 `--exposure`、调高 `--contrast`。
- 想要更强「质感」：调高 `--clarity`（局部对比，核心）。
- 肤色/彩色物体偏灰太多：回调 `--vibrance`（往 0 靠）或 `--saturation`。

## 预设参数（默认配方）

完整参数表与映射逻辑见 `references/preset.md`。默认值：

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

## 处理流程（顺序）

曝光 → 色温 → 高光/阴影 → 黑点 → 对比度 → 鲜明度 → 饱和度 → 清晰度（局部对比）→ 锐化。
每一步均在 [0,1] 浮点空间运算，最终裁剪回合法范围并以 quality=95 保存。

## 注意事项

- 输入若为 CMYK / P 模式会先转 RGB；含透明通道（RGBA/LA）会保留 alpha。
- 大图（长边数千 px）清晰度模糊半径会随尺寸自适应，处理稍慢属正常。
- 本 skill 做「风格化调色」，不做抠图、磨皮、 generative 换背景等复杂编辑。
