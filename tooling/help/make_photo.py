"""Draw the sample files the tour uploads (S103): the lesson's photo of an oil sight glass, a machine's
nameplate photo, and three small one-page PDFs.  Plain drawings, no real plant data.
tour.py calls make_files(); run alone: uv run --project backend python tooling/help/make_photo.py <folder>"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 900


def _font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default()


def sight_glass():
    im = Image.new("RGB", (W, H), (70, 78, 86))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((250, 80, 950, 860), 60, fill=(196, 202, 206), outline=(40, 40, 40), width=6)  # separator tank
    d.ellipse((430, 250, 770, 590), fill=(30, 30, 30))                                                  # glass bezel
    d.ellipse((455, 275, 745, 565), fill=(235, 240, 244))
    d.chord((455, 275, 745, 565), 10, 170, fill=(214, 150, 30))                                         # oil
    d.line((800, 360, 900, 360), fill=(200, 20, 20), width=8)
    d.line((800, 480, 900, 480), fill=(200, 20, 20), width=8)
    f = _font(48)
    d.text((910, 330), "MAX", fill=(200, 20, 20), font=f)
    d.text((910, 450), "MIN", fill=(200, 20, 20), font=f)
    d.text((300, 680), "Oil level between MIN and MAX: OK", fill=(20, 20, 20), font=f)
    return im


def nameplate():
    im = Image.new("RGB", (W, H), (60, 66, 72))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((120, 200, 1080, 700), 30, fill=(205, 208, 212), outline=(30, 30, 30), width=6)
    f = _font(52)
    for n, line in enumerate(("SCREW COMPRESSOR GA37", "Serial no. 0000-0000", "Motor 37 kW   Pressure 7.5 bar",
                              "Year 2020")):
        d.text((180, 250 + n * 105), line, fill=(25, 25, 25), font=f)
    return im


def report(title):
    """A one-page PDF: a title and a few lines of a made-up report."""
    im = Image.new("RGB", (1240, 1754), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((100, 120), title, fill=(20, 20, 20), font=_font(64))
    for n, line in enumerate(("Sample document made for the Help screenshots.", "No real plant data.")):
        d.text((100, 280 + n * 70), line, fill=(60, 60, 60), font=_font(40))
    return im


def make_files(folder):
    """Write the sample files into folder (made if missing); return the folder."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    sight_glass().save(folder / "sight-glass.jpg", "JPEG", quality=88)
    nameplate().save(folder / "compressor-nameplate.jpg", "JPEG", quality=88)
    for name, title in (("compressor-test-report.pdf", "Compressor test report"),
                        ("old-test-report.pdf", "Old test report"),
                        ("ga37-manual.pdf", "GA37 instruction manual")):
        report(title).save(folder / name, "PDF")
    return folder


if __name__ == "__main__":
    make_files(sys.argv[1])
