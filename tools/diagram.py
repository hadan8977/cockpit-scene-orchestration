#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简流程图绘制（PIL），风格对齐 mermaid 默认：圆角浅蓝节点、浅黄分组、菱形判断、带箭头连线。
坐标为逻辑像素，内部 2 倍超采样后缩回。"""
from PIL import Image, ImageDraw, ImageFont
import math

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
NODE_FILL = (236, 240, 250)
NODE_LINE = (60, 60, 70)
DIAMOND_FILL = (255, 242, 204)
GROUP_FILL = (255, 253, 231)
GROUP_LINE = (200, 190, 120)
GREY_FILL = (240, 240, 240)
GREY_LINE = (150, 150, 150)
GREEN_FILL = (228, 245, 232)
TEXT = (30, 30, 30)
MUTED = (120, 120, 120)


class Diagram:
    def __init__(self, w, h, scale=2, font_size=22, bg=(255, 255, 255)):
        self.w, self.h, self.s = w, h, scale
        self.img = Image.new("RGB", (w * scale, h * scale), bg)
        self.d = ImageDraw.Draw(self.img)
        self.font = ImageFont.truetype(FONT, font_size * scale)
        self.small = ImageFont.truetype(FONT, int(font_size * 0.82) * scale)
        self.title_font = ImageFont.truetype(FONT, int(font_size * 0.95) * scale)
        self.nodes = {}

    # ---------- text ----------
    def _wrap(self, text, max_w, font):
        lines = []
        for para in text.split("\n"):
            cur = ""
            for ch in para:
                trial = cur + ch
                if self.d.textlength(trial, font=font) <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = ch
            lines.append(cur)
        return lines

    def _text_block(self, cx, cy, text, max_w, font, fill=TEXT, strike=False):
        lines = self._wrap(text, max_w, font)
        lh = font.size * 1.25
        total = lh * len(lines)
        y = cy - total / 2
        for ln in lines:
            tw = self.d.textlength(ln, font=font)
            x = cx - tw / 2
            self.d.text((x, y), ln, font=font, fill=fill)
            if strike:
                yy = y + font.size * 0.62
                self.d.line([(x, yy), (x + tw, yy)], fill=fill, width=max(2, self.s))
            y += lh

    # ---------- shapes ----------
    def group(self, x, y, w, h, title="", fill=GROUP_FILL, line=GROUP_LINE):
        s = self.s
        self.d.rounded_rectangle([x * s, y * s, (x + w) * s, (y + h) * s], radius=10 * s, fill=fill, outline=line, width=2 * s)
        if title:
            tw = self.d.textlength(title, font=self.title_font)
            self.d.text(((x + w / 2) * s - tw / 2, (y + 8) * s), title, font=self.title_font, fill=TEXT)

    def node(self, nid, x, y, text, w=200, h=70, kind="box", fill=None, line=None, strike=False, dashed=False, small=False):
        """x,y 为中心。kind: box | diamond | plain | grey | green"""
        s = self.s
        font = self.small if small else self.font
        if kind == "diamond":
            fill = fill or DIAMOND_FILL
            pts = [((x) * s, (y - h / 2) * s), ((x + w / 2) * s, y * s), (x * s, (y + h / 2) * s), ((x - w / 2) * s, y * s)]
            self.d.polygon(pts, fill=fill, outline=line or NODE_LINE, width=2 * s)
            self._text_block(x * s, y * s, text, (w * 0.62) * s, font, strike=strike)
        elif kind == "plain":
            self._text_block(x * s, y * s, text, (w - 10) * s, font, fill=MUTED, strike=strike)
        else:
            if kind == "grey":
                fill, line = fill or GREY_FILL, line or GREY_LINE
            elif kind == "green":
                fill = fill or GREEN_FILL
            fill = fill or NODE_FILL
            line = line or NODE_LINE
            box = [(x - w / 2) * s, (y - h / 2) * s, (x + w / 2) * s, (y + h / 2) * s]
            if dashed:
                self._dashed_rect(box, line, 2 * s)
                self.d.rounded_rectangle(box, radius=8 * s, fill=fill, outline=None)
                self._dashed_rect(box, line, 2 * s)
            else:
                self.d.rounded_rectangle(box, radius=8 * s, fill=fill, outline=line, width=2 * s)
            self._text_block(x * s, y * s, text, (w - 16) * s, font, fill=(MUTED if kind == "grey" else TEXT), strike=strike)
        self.nodes[nid] = (x, y, w, h, kind)

    def _dashed_rect(self, box, color, width):
        x0, y0, x1, y1 = box
        for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            self._dashed_line(a, b, color, width, dash=8 * self.s, gap=6 * self.s)

    def _dashed_line(self, a, b, color, width, dash=10, gap=8):
        (x0, y0), (x1, y1) = a, b
        L = math.hypot(x1 - x0, y1 - y0)
        if L == 0:
            return
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        t = 0
        while t < L:
            t2 = min(t + dash, L)
            self.d.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * t2, y0 + uy * t2)], fill=color, width=width)
            t = t2 + gap

    # ---------- edges ----------
    def _anchor(self, nid, side):
        x, y, w, h, kind = self.nodes[nid]
        return {"l": (x - w / 2, y), "r": (x + w / 2, y), "t": (x, y - h / 2), "b": (x, y + h / 2)}[side]

    def _auto_sides(self, a, b):
        ax, ay, aw, ah, _ = self.nodes[a]
        bx, by, bw, bh, _ = self.nodes[b]
        dx, dy = bx - ax, by - ay
        if abs(dx) * (ah / aw if aw else 1) >= abs(dy):
            return ("r", "l") if dx > 0 else ("l", "r")
        return ("b", "t") if dy > 0 else ("t", "b")

    def edge(self, a, b, label="", style="solid", route="straight", sides=None, label_pos=0.5, color=NODE_LINE, label_shift=(0, 0), width=2):
        s = self.s
        sa, sb = sides or self._auto_sides(a, b)
        p0 = self._anchor(a, sa)
        p3 = self._anchor(b, sb)
        pts = [p0]
        if route == "hv":  # 先水平后垂直
            pts.append((p3[0], p0[1]))
        elif route == "vh":
            pts.append((p0[0], p3[1]))
        elif route == "hvh":  # 中点折两次
            mx = (p0[0] + p3[0]) / 2
            pts += [(mx, p0[1]), (mx, p3[1])]
        elif route == "vhv":
            my = (p0[1] + p3[1]) / 2
            pts += [(p0[0], my), (p3[0], my)]
        elif isinstance(route, (list, tuple)):
            pts += list(route)
        pts.append(p3)
        spts = [(x * s, y * s) for x, y in pts]
        for i in range(len(spts) - 1):
            if style == "solid":
                self.d.line([spts[i], spts[i + 1]], fill=color, width=width * s)
            elif style == "dotted":
                self._dashed_line(spts[i], spts[i + 1], color, width * s, dash=3 * s, gap=5 * s)
            else:
                self._dashed_line(spts[i], spts[i + 1], color, width * s, dash=10 * s, gap=7 * s)
        # arrowhead
        (x0, y0), (x1, y1) = spts[-2], spts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        L = 12 * s
        wing = math.radians(26)
        pa = (x1 - L * math.cos(ang - wing), y1 - L * math.sin(ang - wing))
        pb = (x1 - L * math.cos(ang + wing), y1 - L * math.sin(ang + wing))
        self.d.polygon([(x1, y1), pa, pb], fill=color)
        if label:
            # 标签放在总长度 label_pos 处
            seg_lens = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
            total = sum(seg_lens)
            target = total * label_pos
            acc = 0
            lx, ly = pts[-1]
            for i, sl in enumerate(seg_lens):
                if acc + sl >= target and sl > 0:
                    f = (target - acc) / sl
                    lx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f
                    ly = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
                    break
                acc += sl
            lx += label_shift[0]
            ly += label_shift[1]
            tw = self.d.textlength(label, font=self.small)
            th = self.small.size * 1.2
            self.d.rectangle([lx * s - tw / 2 - 4 * s, ly * s - th / 2, lx * s + tw / 2 + 4 * s, ly * s + th / 2], fill=(255, 255, 255))
            self.d.text((lx * s - tw / 2, ly * s - th / 2 + 2 * s), label, font=self.small, fill=(70, 70, 80))

    def note(self, x, y, text, w=300, small=True):
        font = self.small if small else self.font
        self._text_block(x * self.s, y * self.s, text, w * self.s, font, fill=MUTED)

    def save(self, path):
        out = self.img.resize((self.w, self.h), Image.LANCZOS)
        out.save(path, optimize=True)
        print("saved", path, out.size)
