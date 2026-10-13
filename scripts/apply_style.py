#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗调清晰质感 (Dark Tone · Clarity) —— 一键调色脚本

把一组 Lightroom / 泼辣 / Snapseed 风格的「调整」参数固化下来，对照片做：
  压暗曝光 → 冷暖微调 → 高光提亮/阴影压暗 → 黑点微抬 → 提升对比
  → 去饱和(鲜明度+饱和度两次) → 局部对比(清晰度) → 锐化

所有参数默认就是你给定的预设值，可在命令行逐个覆盖，例如：
  python apply_style.py photo.jpg
  python apply_style.py photo.jpg -o out.jpg --exposure -30 --clarity 80
  python apply_style.py photo.jpg --intensity 0.6      # 整体强度 0~1

依赖：Pillow, numpy  (pip install Pillow numpy)
"""

import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

# ----------------------------------------------------------------------------
# 预设参数（全部基于 -100 ~ +100 的「调整面板」量纲）
# 这是「暗调清晰质感」默认配方，可按需通过命令行覆盖。
# ----------------------------------------------------------------------------
PRESET = {
    "exposure":    -23,   # 曝光：整体亮度（EV 映射）
    "vibrance":    -48,   # 鲜明度：选择性去饱和（保肤色/中性灰）
    "highlights":   34,   # 高光：正值=提亮亮部（保留高光细节）
    "shadows":     -16,   # 阴影：负值=压暗暗部
    "contrast":     42,   # 对比度：S 型拉伸
    "blacks":       10,   # 黑点：正值=微抬纯黑（胶片感，避免死黑）
    "saturation":  -25,   # 饱和度：全局去饱和
    "temperature": -10,   # 色温：负值=偏冷
    "sharpness":    35,   # 锐度：USM 锐化
    "clarity":      65,   # 清晰度：局部对比（质感核心）
}

# 各参数到实际运算的缩放系数（经验值，保证 -100~+100 落在合理视觉区间）
_SCALE = {
    "exposure":    1.5,    # EV 上限 ±1.5
    "vibrance":    1.0,
    "highlights":  0.30,
    "shadows":     0.30,
    "contrast":    0.70,
    "blacks":      0.15,
    "saturation":  1.0,
    "temperature": 0.08,
    "sharpness":   1.0,
    "clarity":     1.0,
}


# ----------------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------------
def _luminance(rgb):
    """Rec.709 亮度。rgb: (H,W,3) float[0,1] -> (H,W)"""
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def _gaussian_1ch(arr_uint8, radius):
    """对单通道 uint8 数组做高斯模糊，返回 float[0,1] 数组"""
    im = Image.fromarray(arr_uint8, "L").filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(im, dtype=np.float32) / 255.0


def _pix_saturation(rgb):
    """逐像素饱和度度量 S∈[0,1]，用于鲜明度(保中性)。"""
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    return (mx - mn) / np.clip(mx, 1e-4, None)


# ----------------------------------------------------------------------------
# 各调整步骤
# ----------------------------------------------------------------------------
def _exposure(rgb, v, intensity):
    ev = (v / 100.0) * _SCALE["exposure"] * intensity
    return rgb * (2.0 ** ev)


def _temperature(rgb, v, intensity):
    t = (v / 100.0) * _SCALE["temperature"] * intensity
    # 负值=偏冷：红降、蓝升
    r = rgb[:, :, 0] * (1.0 + t)
    b = rgb[:, :, 2] * (1.0 - t)
    out = rgb.copy()
    out[:, :, 0] = r
    out[:, :, 2] = b
    return out


def _tone_hl_sh(rgb, hl, sh, intensity, max_dim):
    L = _luminance(rgb)
    Ls = L + 1e-4
    hl_amt = (hl / 100.0) * _SCALE["highlights"] * intensity
    sh_amt = (sh / 100.0) * _SCALE["shadows"] * intensity
    # 亮部掩码（亮处有效）、暗部掩码（暗处有效）
    m_h = np.clip((L - 0.5) / 0.5, 0.0, 1.0) ** 2
    m_s = np.clip((0.5 - L) / 0.5, 0.0, 1.0) ** 2
    L_new = L + hl_amt * m_h + sh_amt * m_s
    factor = np.clip(L_new / Ls, 0.0, 2.0)
    return rgb * factor[:, :, None]


def _blacks(rgb, v, intensity, max_dim):
    bl = (v / 100.0) * _SCALE["blacks"] * intensity
    floor = max(0.0, bl)  # 仅正值时抬黑点
    return rgb * (1.0 - floor) + floor


def _contrast(rgb, v, intensity):
    c = 1.0 + (v / 100.0) * _SCALE["contrast"] * intensity
    return (rgb - 0.5) * c + 0.5


def _vibrance(rgb, v, intensity):
    # 鲜明度：去饱和时保护低饱和（中性灰/肤色）
    L = _luminance(rgb)[:, :, None]
    S = _pix_saturation(rgb)[:, :, None]
    vv = (v / 100.0) * _SCALE["vibrance"] * intensity  # 负数=去饱和
    mult = 1.0 - (-vv) * S
    return L + (rgb - L) * mult


def _saturation(rgb, v, intensity):
    L = _luminance(rgb)[:, :, None]
    s = 1.0 + (v / 100.0) * _SCALE["saturation"] * intensity
    return L + (rgb - L) * s


def _clarity(rgb, v, intensity, max_dim):
    # 局部对比：用大半径高斯得到「低频」，原图减低频=中频细节，加回去
    L = _luminance(rgb)
    radius = max(8, min(80, int(max_dim / 25.0)))
    blurred = _gaussian_1ch((np.clip(L, 0, 1) * 255).astype(np.uint8), radius)
    detail = L - blurred
    L_new = L + detail * (v / 100.0) * _SCALE["clarity"] * intensity
    Ls = L + 1e-4
    factor = np.clip(L_new / Ls, 0.0, 2.0)
    return rgb * factor[:, :, None]


def _sharpness(rgb, v, intensity, max_dim):
    # USM 锐化：小半径高斯，原图减模糊得到边缘，加回去
    radius = max(1, int(round(max_dim / 1000.0)))  # 约 1px@1000
    out = rgb.copy()
    for c in range(3):
        ch = np.clip(rgb[:, :, c], 0, 1)
        blurred = _gaussian_1ch((ch * 255).astype(np.uint8), radius)
        edge = ch - blurred
        out[:, :, c] = ch + edge * (v / 100.0) * _SCALE["sharpness"] * intensity
    return out


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def stylize(img, p, intensity=1.0):
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    max_dim = max(rgb.shape[0], rgb.shape[1])

    rgb = _exposure(rgb, p["exposure"], intensity)
    rgb = _temperature(rgb, p["temperature"], intensity)
    rgb = _tone_hl_sh(rgb, p["highlights"], p["shadows"], intensity, max_dim)
    rgb = _blacks(rgb, p["blacks"], intensity, max_dim)
    rgb = _contrast(rgb, p["contrast"], intensity)
    rgb = np.clip(rgb, 0.0, 1.0)          # 在进入色彩/质感前先收敛
    rgb = _vibrance(rgb, p["vibrance"], intensity)
    rgb = _saturation(rgb, p["saturation"], intensity)
    rgb = _clarity(rgb, p["clarity"], intensity, max_dim)
    rgb = _sharpness(rgb, p["sharpness"], intensity, max_dim)
    rgb = np.clip(rgb, 0.0, 1.0)
    return Image.fromarray((rgb * 255).astype(np.uint8), "RGB")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="暗调清晰质感：把照片调成压暗、强对比、去饱和、冷调、锐利的电影感暗调。")
    ap.add_argument("input", help="输入图片路径")
    ap.add_argument("-o", "--output", help="输出路径（默认 <名>_darktone.<ext>）")
    ap.add_argument("--intensity", type=float, default=1.0,
                    help="整体强度 0~1（默认 1.0，乘以所有调整量）")
    for k, val in PRESET.items():
        ap.add_argument("--" + k, type=float, default=None,
                        help=f"{k}（预设 {val}，量纲 -100~+100）")
    ap.add_argument("--show-params", action="store_true", help="打印生效参数后退出")
    args = ap.parse_args(argv)

    p = dict(PRESET)
    for k in PRESET:
        v = getattr(args, k)
        if v is not None:
            p[k] = v

    if args.show_params:
        print("生效参数 (intensity={}):".format(args.intensity))
        for k in PRESET:
            print(f"  {k:11s} {p[k]:+7.0f}")
        return 0

    if not os.path.isfile(args.input):
        print(f"错误：找不到输入文件 {args.input}", file=sys.stderr)
        return 2

    src = Image.open(args.input)
    src = ImageOps.exif_transpose(src)  # 尊重拍摄方向
    has_alpha = src.mode in ("RGBA", "LA")
    if has_alpha:
        alpha = src.split()[-1]
    if src.mode not in ("RGB", "RGBA", "L", "LA"):
        src = src.convert("RGB")
    elif src.mode in ("L", "LA"):
        src = src.convert("RGB")
    else:
        src = src.convert("RGB")

    out = stylize(src, p, intensity=args.intensity)
    if has_alpha:
        out = out.convert("RGBA")
        out.putalpha(alpha)

    out_path = args.output or (
        os.path.splitext(args.input)[0] + "_darktone"
        + os.path.splitext(args.input)[1])
    out.save(out_path, quality=95)
    print(f"已保存：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
