# -*- coding: utf-8 -*-
"""
生成 og:image 分享图（1200x630 PNG）。

为什么必须是 PNG 而不是 SVG：
    主流社交平台的 OG 图爬虫（微信、QQ、Facebook、Twitter 等）都不解析 SVG，
    只接受 PNG / JPG / GIF。本站原来的 og:image 指向 og-cover.svg，
    既文件不存在、格式也不被支持 —— 双重失效。

用法：
    python tools/make_og_cover.py
输出：
    static/assets/og-cover.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "assets", "og-cover.png")

W, H = 1200, 630

# 与 static/assets/style.css 的 CSS 变量保持一致
BRAND = (13, 79, 139)        # --brand  #0d4f8b
BRAND_2 = (26, 111, 189)     # --brand-2 #1a6fbd
ACCENT = (180, 83, 10)       # --accent  #b4530a
INK = (27, 36, 48)           # --ink     #1b2430
INK_2 = (67, 83, 106)        # --ink-2   #43536a
LINE = (223, 229, 238)       # --line    #dfe5ee
BG_SOFT = (245, 248, 252)    # --bg-soft #f5f8fc
WHITE = (255, 255, 255)

FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG = "C:/Windows/Fonts/msyh.ttc"


def font(path, size):
    return ImageFont.truetype(path, size)


def trapezoid(draw, cx, top, w_top, w_bot, h, fill, outline=None, width=0):
    """画一个梯形（模拟三角带截面）"""
    half_t, half_b = w_top / 2, w_bot / 2
    pts = [(cx - half_t, top), (cx + half_t, top),
           (cx + half_b, top + h), (cx - half_b, top + h)]
    draw.polygon(pts, fill=fill, outline=outline, width=width)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # ---- 背景：右侧淡蓝色块 + 底部细线
    d.rectangle([0, 0, W, H], fill=WHITE)
    d.rectangle([820, 0, W, H], fill=BG_SOFT)
    d.rectangle([0, H - 8, W, H], fill=BRAND)
    d.rectangle([0, H - 8, 360, H], fill=ACCENT)

    # ---- 左侧：品牌竖条
    d.rectangle([72, 92, 84, 300], fill=BRAND)

    # ---- 主标题
    f_title = font(FONT_BOLD, 78)
    d.text((116, 88), "三角带行业资讯", font=f_title, fill=BRAND)

    # ---- 副标题（栏目轴）
    f_sub = font(FONT_REG, 34)
    d.text((118, 200), "型号规格 · 选型计算 · 安装维护 · 失效排查",
           font=f_sub, fill=INK_2)

    # ---- 域名
    f_dom = font(FONT_BOLD, 36)
    d.text((118, 268), "三角带.com", font=f_dom, fill=ACCENT)

    # ---- 分隔线
    d.line([(118, 350), (770, 350)], fill=LINE, width=2)

    # ---- 说明文字
    f_desc = font(FONT_REG, 27)
    d.text((118, 380), "面向机械传动行业的采购与技术人员", font=f_desc, fill=INK)
    d.text((118, 424), "普通 V 带 Y/Z/A/B/C/D/E 与窄 V 带 SPZ/SPA/SPB/SPC",
           font=f_desc, fill=INK_2)

    # ---- 右侧：V 带截面示意（截面尺寸递增，呼应型号序列）
    # 注意：间距固定时，底部宽度必须小于间距，否则相邻梯形会重叠
    f_lbl = font(FONT_REG, 20)
    base_y = 250
    CELL = 56                       # 单元格间距
    specs = [("Y", 8, 18, 30), ("Z", 11, 23, 38), ("A", 14, 28, 46),
             ("B", 17, 34, 54), ("C", 20, 40, 62), ("D", 23, 46, 70)]
    x = 862
    for name, wt, wb, hh in specs:
        top = base_y + (70 - hh) // 2
        trapezoid(d, x, top, wt, wb, hh, fill=BRAND)
        tw = d.textlength(name, font=f_lbl)
        d.text((x - tw / 2, base_y + 92), name, font=f_lbl, fill=INK_2)
        x += CELL
    d.text((862, base_y - 62), "普通 V 带截面系列", font=font(FONT_REG, 22), fill=INK_2)

    img.save(OUT, "PNG", optimize=True)
    print("已生成 %s  (%d x %d, %.1f KB)"
          % (OUT, W, H, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
