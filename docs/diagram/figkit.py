"""Mini-moteur de figures : une seule description produit un SVG (→ PNG) et un
fichier draw.io éditable aux coordonnées identiques.

Charte reprise du rapport : bleu 1F4E79, fond EAEFF5, bordures BFBFBF,
police Carlito (équivalent métrique de Calibri). Pictogrammes génériques
Font Awesome (licence CC BY 4.0), exportés par export_icons.js.
"""
from __future__ import annotations

import base64
import html
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICONS = json.loads((HERE / "icons.json").read_text())

BLUE = "#1F4E79"
BLUE_MID = "#2E75B6"
FILL = "#EAEFF5"
LINE = "#BFBFBF"
INK = "#222222"
GREY = "#595959"
LIGHT = "#F6F7F8"
ORANGE = "#C55A11"
GREEN = "#548235"
FONT = "Carlito, Calibri, Arial, sans-serif"


def icon_svg(name: str, color: str = "#FFFFFF") -> str:
    return ICONS[name].replace('fill="currentColor"', f'fill="{color}"').replace('color="#FFFFFF"', "").replace(
        'stroke="currentColor"', f'stroke="{color}"').replace("#FFFFFF", color)


def icon_data_uri(name: str, color: str = "#FFFFFF") -> str:
    svg = icon_svg(name, color)
    if 'xmlns="http://www.w3.org/2000/svg"' not in svg:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return base64.b64encode(svg.encode()).decode()


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    fill: str = "#FFFFFF"
    stroke: str = BLUE
    sw: float = 1.4
    r: float = 6
    dash: bool = False
    shadow: bool = False


@dataclass
class Text:
    x: float
    y: float
    w: float
    lines: list[str]
    size: float = 13
    color: str = INK
    bold: bool = False
    italic: bool = False
    align: str = "middle"       # start | middle | end
    lh: float = 1.3


@dataclass
class Icon:
    name: str
    cx: float
    cy: float
    d: float = 46               # diamètre du disque
    bg: str = BLUE
    fg: str = "#FFFFFF"


@dataclass
class Badge:
    cx: float
    cy: float
    label: str
    d: float = 24
    bg: str = "#FFFFFF"
    fg: str = BLUE
    stroke: str = BLUE


@dataclass
class Arrow:
    pts: list[tuple[float, float]]
    color: str = BLUE
    sw: float = 1.8
    dash: bool = False
    label: str = ""
    label_at: tuple[float, float] | None = None
    label_w: float = 0
    both: bool = False


@dataclass
class Figure:
    w: float
    h: float
    title: str = ""
    items: list = field(default_factory=list)
    bg: str = LIGHT

    def add(self, *it):
        self.items.extend(it)
        return self

    # ------------------------------------------------------------- SVG
    def svg(self) -> str:
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
               "<defs>"]
        colors = {a.color for a in self.items if isinstance(a, Arrow)}
        for c in colors:
            cid = c.strip("#")
            out.append(f'<marker id="m{cid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                       f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
        out.append('<filter id="sh" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="1.5" '
                   'stdDeviation="1.5" flood-color="#000" flood-opacity="0.10"/></filter></defs>')
        out.append(f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>')
        if self.title:
            out.append(f'<text x="{self.w / 2}" y="34" text-anchor="middle" font-family="{FONT}" font-size="21" '
                       f'font-weight="700" fill="{INK}">{html.escape(self.title)}</text>')
        for it in self.items:
            out.append(self._svg_item(it))
        out.append("</svg>")
        return "\n".join(out)

    def _svg_item(self, it) -> str:
        if isinstance(it, Rect):
            dash = ' stroke-dasharray="6 4"' if it.dash else ""
            sh = ' filter="url(#sh)"' if it.shadow else ""
            return (f'<rect x="{it.x}" y="{it.y}" width="{it.w}" height="{it.h}" rx="{it.r}" fill="{it.fill}" '
                    f'stroke="{it.stroke}" stroke-width="{it.sw}"{dash}{sh}/>')
        if isinstance(it, Text):
            x = {"start": it.x, "middle": it.x + it.w / 2, "end": it.x + it.w}[it.align]
            s = []
            for i, ln in enumerate(it.lines):
                y = it.y + it.size + i * it.size * it.lh
                st = (' font-weight="700"' if it.bold else "") + (' font-style="italic"' if it.italic else "")
                s.append(f'<text x="{x}" y="{y:.1f}" text-anchor="{it.align}" font-family="{FONT}" '
                         f'font-size="{it.size}" fill="{it.color}"{st}>{html.escape(ln)}</text>')
            return "\n".join(s)
        if isinstance(it, Icon):
            s = it.d * 0.5
            inner = icon_svg(it.name, it.fg).replace('height="64"', f'height="{s}"').replace('width="64"', f'width="{s}"')
            inner = inner.replace("<svg", f'<svg x="{it.cx - s / 2}" y="{it.cy - s / 2}"', 1)
            return f'<circle cx="{it.cx}" cy="{it.cy}" r="{it.d / 2}" fill="{it.bg}"/>{inner}'
        if isinstance(it, Badge):
            return (f'<circle cx="{it.cx}" cy="{it.cy}" r="{it.d / 2}" fill="{it.bg}" stroke="{it.stroke}" stroke-width="1.4"/>'
                    f'<text x="{it.cx}" y="{it.cy + it.d * 0.2}" text-anchor="middle" font-family="{FONT}" '
                    f'font-size="{it.d * 0.55}" font-weight="700" fill="{it.fg}">{html.escape(it.label)}</text>')
        if isinstance(it, Arrow):
            d = "M " + " L ".join(f"{x} {y}" for x, y in it.pts)
            dash = ' stroke-dasharray="7 5"' if it.dash else ""
            mid = f"m{it.color.strip('#')}"
            st = f' marker-start="url(#{mid})"' if it.both else ""
            s = [f'<path d="{d}" fill="none" stroke="{it.color}" stroke-width="{it.sw}"{dash} stroke-linejoin="round" '
                 f'marker-end="url(#{mid})"{st}/>']
            if it.label:
                lx, ly = it.label_at
                lw = it.label_w or len(it.label) * 6.3 + 12
                s.append(f'<rect x="{lx - lw / 2}" y="{ly - 10}" width="{lw}" height="20" rx="3" fill="#FFFFFF" '
                         f'stroke="{LINE}" stroke-width="0.8"/>')
                s.append(f'<text x="{lx}" y="{ly + 4.5}" text-anchor="middle" font-family="{FONT}" font-size="12" '
                         f'fill="{it.color}">{html.escape(it.label)}</text>')
            return "\n".join(s)
        raise TypeError(it)

    def png(self, path: Path, scale: float = 2.0) -> None:
        import cairosvg
        cairosvg.svg2png(bytestring=self.svg().encode(), write_to=str(path), output_width=int(self.w * scale))

    # ---------------------------------------------------------- DRAWIO
    def drawio(self, name: str) -> str:
        mx = ET.Element("mxfile", host="app.diagrams.net", type="device")
        dg = ET.SubElement(mx, "diagram", id=name.replace(" ", "-")[:40], name=name)
        gm = ET.SubElement(dg, "mxGraphModel", dx=str(int(self.w)), dy=str(int(self.h)), grid="1", gridSize="10",
                           guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1",
                           pageWidth=str(int(self.w)), pageHeight=str(int(self.h)), math="0", shadow="0",
                           background=self.bg)
        root = ET.SubElement(gm, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        n = [0]

        def nid():
            n[0] += 1
            return f"c{n[0]}"

        def vcell(value, style, x, y, w, h):
            c = ET.SubElement(root, "mxCell", id=nid(), value=value, style=style, vertex="1", parent="1")
            ET.SubElement(c, "mxGeometry", x=f"{x:g}", y=f"{y:g}", width=f"{w:g}", height=f"{h:g}", **{"as": "geometry"})

        if self.title:
            vcell(html.escape(self.title), f"text;html=1;align=center;verticalAlign=middle;fontFamily=Calibri;fontSize=21;"
                  f"fontStyle=1;fontColor={INK};", 0, 14, self.w, 30)
        for it in self.items:
            if isinstance(it, Rect):
                vcell("", f"rounded=1;absoluteArcSize=1;arcSize={it.r * 2:g};whiteSpace=wrap;html=1;fillColor={it.fill};"
                      f"strokeColor={it.stroke};strokeWidth={it.sw:g};" + ("dashed=1;dashPattern=6 4;" if it.dash else "")
                      + ("shadow=1;" if it.shadow else ""), it.x, it.y, it.w, it.h)
            elif isinstance(it, Text):
                al = {"start": "left", "middle": "center", "end": "right"}[it.align]
                fs = (1 if it.bold else 0) + (2 if it.italic else 0)
                val = "<br>".join(html.escape(ln) for ln in it.lines)
                h = it.size * it.lh * len(it.lines) + 4
                vcell(val, f"text;html=1;whiteSpace=wrap;align={al};verticalAlign=top;spacing=0;fontFamily=Calibri;"
                      f"fontSize={it.size:g};fontColor={it.color};fontStyle={fs};", it.x, it.y, it.w, h)
            elif isinstance(it, Icon):
                vcell("", f"ellipse;whiteSpace=wrap;html=1;fillColor={it.bg};strokeColor=none;",
                      it.cx - it.d / 2, it.cy - it.d / 2, it.d, it.d)
                s = it.d * 0.5
                vcell("", f"shape=image;html=1;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=1;aspect=fixed;"
                      f"image=data:image/svg+xml,{icon_data_uri(it.name, it.fg)};", it.cx - s / 2, it.cy - s / 2, s, s)
            elif isinstance(it, Badge):
                vcell(html.escape(it.label), f"ellipse;whiteSpace=wrap;html=1;fillColor={it.bg};strokeColor={it.stroke};"
                      f"strokeWidth=1.4;fontFamily=Calibri;fontStyle=1;fontSize={it.d * 0.55:g};fontColor={it.fg};",
                      it.cx - it.d / 2, it.cy - it.d / 2, it.d, it.d)
            elif isinstance(it, Arrow):
                style = (f"endArrow=block;endFill=1;html=1;rounded=0;strokeColor={it.color};strokeWidth={it.sw:g};"
                         + ("dashed=1;dashPattern=7 5;" if it.dash else "")
                         + ("startArrow=block;startFill=1;" if it.both else ""))
                c = ET.SubElement(root, "mxCell", id=nid(), value="", style=style, edge="1", parent="1")
                g = ET.SubElement(c, "mxGeometry", relative="1", **{"as": "geometry"})
                ET.SubElement(g, "mxPoint", x=f"{it.pts[0][0]:g}", y=f"{it.pts[0][1]:g}", **{"as": "sourcePoint"})
                ET.SubElement(g, "mxPoint", x=f"{it.pts[-1][0]:g}", y=f"{it.pts[-1][1]:g}", **{"as": "targetPoint"})
                if len(it.pts) > 2:
                    arr = ET.SubElement(g, "Array", **{"as": "points"})
                    for x, y in it.pts[1:-1]:
                        ET.SubElement(arr, "mxPoint", x=f"{x:g}", y=f"{y:g}")
                if it.label:
                    lx, ly = it.label_at
                    lw = it.label_w or len(it.label) * 6.3 + 12
                    vcell(html.escape(it.label), f"rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={LINE};"
                          f"fontFamily=Calibri;fontSize=12;fontColor={it.color};", lx - lw / 2, ly - 10, lw, 20)
        ET.indent(mx)
        return ET.tostring(mx, encoding="unicode")

    def save(self, stem: Path, name: str, scale: float = 2.0) -> None:
        stem.parent.mkdir(parents=True, exist_ok=True)
        stem.with_suffix(".svg").write_text(self.svg(), encoding="utf-8")
        stem.with_suffix(".drawio").write_text(self.drawio(name), encoding="utf-8")
        self.png(stem.with_suffix(".png"), scale)


# ------------------------------------------------------------ composants
def card(fig: Figure, x, y, w, h, title, desc: list[str], icon: str | None = None, tag: str | None = None,
         num: str | None = None, accent: str = BLUE, fill: str = "#FFFFFF", title_size: float = 15,
         desc_size: float = 12.5, icon_d: float = 46) -> None:
    """Carte standard : pictogramme en haut, titre, description, étiquette d'outil en bas."""
    fig.add(Rect(x, y, w, h, fill=fill, stroke=accent, shadow=True))
    cy = y + 16
    if icon:
        fig.add(Icon(icon, x + w / 2, y + 16 + icon_d / 2, d=icon_d, bg=accent))
        cy = y + 24 + icon_d
    if num:
        fig.add(Badge(x + 18, y + 18, num, d=24, fg=accent, stroke=accent))
    fig.add(Text(x + 8, cy, w - 16, [title], size=title_size, bold=True, color=accent))
    fig.add(Text(x + 10, cy + title_size + 10, w - 20, desc, size=desc_size, color=GREY))
    if tag:
        tw = len(tag) * 6.6 + 22
        fig.add(Rect(x + (w - tw) / 2, y + h - 34, tw, 22, fill=FILL, stroke=FILL, r=11, sw=1))
        fig.add(Text(x + (w - tw) / 2, y + h - 31, tw, [tag], size=12, bold=True, color=accent))


def note(fig: Figure, y, lines: list[str], size=12.5, color=GREY, italic=True, bold=False):
    fig.add(Text(0, y, fig.w, lines, size=size, color=color, italic=italic, bold=bold))
