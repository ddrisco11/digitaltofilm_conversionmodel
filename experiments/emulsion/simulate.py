"""Render an sRGB image and inspect the neutral and primary-light bench targets."""
import argparse
import json
from pathlib import Path

import colour
import numpy as np
from PIL import Image, ImageOps
from scipy.special import gammainc

SHAPE = colour.SpectralShape(400, 700, 5)
WAVE = np.arange(400, 701, 5)
RGB = colour.RGB_COLOURSPACES["sRGB"]


def bands(centers, widths):
    return np.exp(-0.5 * ((WAVE[:, None] - centers) / widths) ** 2)


def develop(exposure, rng=None):
    fraction = np.zeros_like(exposure)
    for speed in (2, 10, 50):
        probability = gammainc(4, exposure * speed)
        fraction += probability if rng is None else rng.binomial(128, probability) / 128
    return fraction / 3


class Emulsion:
    def __init__(self):
        display = colour.characterisation.MSDS_DISPLAY_PRIMARIES["Apple Studio Display"].copy().align(SHAPE).values
        cmf = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"].copy().align(SHAPE).values
        self.drive = RGB.matrix_RGB_to_XYZ.T @ np.linalg.inv(display.T @ cmf)
        self.drive /= (np.ones(3) @ self.drive).max()
        # Effective sensitivities of the coated stack. Wavelength weights convert
        # relative radiant energy to relative photon number (common hc cancels).
        sensitivity = bands([615, 540, 455], [28, 23, 22]) * WAVE[:, None]
        self.expose = display.T @ sensitivity
        self.expose /= np.clip(np.ones(3) @ self.drive, 0, 1) @ self.expose
        # Ideal balanced CMY dyes: equal dye loads have constant spectral density.
        dyes = bands([625, 540, 450], [43, 35, 35])
        self.dyes = (dyes / dyes.sum(axis=1, keepdims=True)).T
        lamp = colour.SDS_ILLUMINANTS["D50"].copy().align(SHAPE).values
        receiver = lamp[:, None] * sensitivity
        self.paper = receiver / receiver.sum(axis=0)
        observer = lamp[:, None] * cmf
        observer /= observer[:, 1].sum()
        white = colour.XYZ_to_xy(observer.sum(axis=0))
        self.viewer = observer @ colour.XYZ_to_RGB(np.eye(3), RGB, illuminant=white,
                                                   chromatic_adaptation_transform="Bradford")

    def write(self, code, rng=None):
        drive = np.clip(colour.models.eotf_sRGB(code) @ self.drive, 0, 1)
        exposure = drive @ self.expose
        return exposure, develop(exposure, rng)

    def print_negative(self, amounts):
        transmission = 10 ** (-0.10 - 2.0 * (amounts @ self.dyes))
        paper_exposure = transmission @ self.paper
        # Smooth saturating response of an invented print material.
        paper_dye = 1 / (1 + (0.12 / paper_exposure) ** 2)
        reflectance = 10 ** (-2.0 * (paper_dye @ self.dyes))
        return transmission @ self.viewer, paper_exposure, reflectance @ self.viewer


def encode(linear):
    return np.rint(255 * colour.models.eotf_inverse_sRGB(np.clip(linear, 0, 1))).astype('uint8')


def checks(stock):
    labels = ['red', 'green', 'blue'] + [f'gray-{i}' for i in range(17)]
    targets = np.vstack((np.eye(3), np.repeat(np.linspace(0, 1, 17)[:, None], 3, axis=1)))
    exposure, amounts = stock.write(targets)
    _, paper, output = stock.print_negative(amounts)
    result = encode(output)
    assert np.array_equal(exposure[:3].argmax(axis=1), np.arange(3))
    assert np.array_equal(amounts[:3].argmax(axis=1), np.arange(3))
    assert np.array_equal(paper[:3].argmin(axis=1), np.arange(3))
    assert np.array_equal(result[:3].argmax(axis=1), np.arange(3))
    assert np.max(np.ptp(result[3:].astype(int), axis=1)) <= 1
    assert (np.diff(output[3:], axis=0) >= -1e-9).all()
    return {label: dict(layer_exposure=h.tolist(), cmy=d.tolist(), paper_exposure=p.tolist(),
                        output_srgb8=r.tolist()) for label,h,d,p,r in zip(labels,exposure,amounts,paper,result)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('photo', help='sRGB input image')
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    stock = Emulsion()
    diagnostics = checks(stock)
    (args.out/'bench.json').write_text(json.dumps(diagnostics, indent=2))
    original = ImageOps.exif_transpose(Image.open(args.photo)).convert('RGB')
    pixels = np.asarray(original)
    rng = np.random.default_rng(63)
    negative, positive = (np.empty_like(pixels) for _ in range(2))
    for y in range(0, original.height, 12):
        rows = slice(y,y+12)
        code = pixels[rows] / 255.
        _, amounts = stock.write(code, rng)
        neg, _, pos = stock.print_negative(amounts)
        negative[rows], positive[rows] = encode(neg), encode(pos)
    for name, array in [('negative',negative), ('print',positive)]:
        Image.fromarray(array).save(args.out / (name+'.png'))
    comparison = Image.new('RGB',(1200,round(600*original.height/original.width)))
    for x,im in [(0,original),(600,Image.fromarray(positive))]:
        comparison.paste(im.resize((600,comparison.height),Image.Resampling.LANCZOS),(x,0))
    comparison.save(args.out/'comparison.jpg',quality=94)
