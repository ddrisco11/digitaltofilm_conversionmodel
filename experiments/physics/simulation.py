"""Relative radiometry of a displayed image photographed on negative film, then printed."""
import json
from pathlib import Path

import colour
import numpy as np
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
MATERIALS = HERE / "materials"
SHAPE = colour.SpectralShape(405, 695, 5)
WL = np.arange(405, 696, 5)
STEP = 5.0
GRAY = 0.184
RGB = colour.RGB_COLOURSPACES["sRGB"]


def profile(name):
    meta = json.loads((MATERIALS / (name + ".json")).read_text())["data"]
    mask = np.isin(meta["wavelengths"], WL)
    get = lambda key: np.asarray(meta[key], dtype=float)[mask]
    response = np.array(meta["density_curves"], dtype=float)
    result = dict(sensitivity=10**get("log_sensitivity"), dyes=get("channel_density"),
                  base=get("base_density"), exposure=np.array(meta["log_exposure"]),
                  curves=np.maximum(response - response.min(axis=0), 0))
    for array in result.values():
        assert np.isfinite(array).all()
    return result


def develop(exposure, stock):
    log_h = np.log10(np.maximum(exposure, 1e-12))
    return np.column_stack([np.interp(log_h[:, c], stock["exposure"], stock["curves"][:, c])
                            for c in range(3)])


def transmission(amounts, stock):
    spectral_density = amounts @ stock["dyes"].T + stock["base"]
    return 10**(-np.maximum(spectral_density, 0))


def srgb(linear):
    return colour.models.eotf_inverse_sRGB(np.clip(linear, 0, 1))


def linear(code):
    return colour.models.eotf_sRGB(code)


class CameraAndPrinter:
    def __init__(self):
        self.film = profile("kodak_portra_400")
        self.paper = profile("kodak_portra_endura")
        cmf = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"].copy().align(SHAPE).values
        self.primaries = colour.characterisation.MSDS_DISPLAY_PRIMARIES["Apple Studio Display"].copy().align(SHAPE).values
        self.drive = RGB.matrix_RGB_to_XYZ.T @ np.linalg.inv(self.primaries.T @ cmf * STEP)
        self.drive /= np.max(np.ones(3) @ self.drive)
        self.film_matrix = self.primaries.T @ self.film["sensitivity"] * STEP
        self.exposure_scale = 1 / ((np.full(3, GRAY) @ self.drive) @ self.film_matrix)[1]
        view = colour.SDS_ILLUMINANTS["D50"].copy().align(SHAPE).values
        self.observer = view[:, None]*cmf / np.sum(view*cmf[:, 1])
        xy = colour.XYZ_to_xy(self.observer.sum(axis=0))
        self.to_rgb = colour.XYZ_to_RGB(np.eye(3), RGB, illuminant=xy,
                                       chromatic_adaptation_transform="Bradford")
        lam = WL * 1e-9
        self.lamp = lam**-5/np.expm1(.01438776877/(lam*3200))
        self.lamp /= self.lamp.max()
        filters = []
        for channel in "cmy":
            a = np.loadtxt(MATERIALS / f"filter_{channel}.csv", delimiter=",")
            x, i = np.unique(a[:, 0], return_index=True)
            filters.append(np.clip(np.interp(WL, x, a[i, 1])/100, 0, 1))
        self.filters = np.array(filters)
        mid = self.negative_density(np.full((1,3),GRAY))
        # A real head permits a common neutral attenuation to be traded for time.
        # Try each two-filter pack, keep the smallest gray-reference residual.
        candidates=[]
        for omitted in range(3):
            active=np.arange(3)!=omitted
            def settings(x):
                f=np.zeros(3); f[active]=x[:2]
                return self.lamp*np.prod(1-f[:,None]+f[:,None]*self.filters,axis=0)*10**x[2], f
            def residual(x):
                light,_=settings(x)
                p=develop((transmission(mid,self.film)*light)@self.paper["sensitivity"]*STEP,self.paper)
                return (self.reflect(p)@self.to_rgb)[0]-GRAY
            fit=least_squares(residual,[.5,.5,-1],bounds=([0,0,-6],[1,1,6]),gtol=1e-13,ftol=1e-13,xtol=1e-13)
            light,filters_used=settings(fit.x)
            candidates.append((np.linalg.norm(fit.fun),light,filters_used,fit.x[2]))
        self.gray_error,self.print_light,self.insertions,self.log_print_time=min(candidates,key=lambda v:v[0])
        self.print_matrix=self.print_light[:,None]*self.paper["sensitivity"]*STEP

    def expose(self, linear_rgb, ev=0):
        drive=np.clip(linear_rgb@self.drive,0,1)
        return drive @ self.film_matrix * self.exposure_scale * 2.0**ev

    def negative_density(self, linear_rgb, ev=0):
        return develop(self.expose(linear_rgb,ev),self.film)

    def reflect(self, paper_dye):
        return transmission(paper_dye,self.paper) @ self.observer

    def stages(self, code, ev=0):
        h=self.expose(linear(code),ev)
        cmy=develop(h,self.film)
        t=transmission(cmy,self.film)
        p_h=t@self.print_matrix
        p_cmy=develop(p_h,self.paper)
        xyz=self.reflect(p_cmy)
        return h,cmy,t,p_h,p_cmy,xyz

    def render(self, code, ev=0):
        return srgb(self.stages(code,ev)[-1]@self.to_rgb)
