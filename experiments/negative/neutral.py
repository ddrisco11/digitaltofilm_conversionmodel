"""Calibrate a virtual gray ramp before exposing a scene. Uses no scene reference."""
import numpy as np
from negative_pipeline import as_density,develop,make_negative


def calibrate(model):
    grays=np.linspace(.12,.9,16)
    colors=np.repeat(grays[:,None,None],3,axis=2)
    d=as_density(make_negative(colors,model))
    span=model['hi']-model['lo']
    def residual(params):
        bias,gain=params[:3],params[3:]
        adjusted=d+span*bias+(d-(model['lo']+model['hi'])/2)*gain
        pred=develop(10**(-adjusted),model)
        return np.r_[(pred-colors).ravel(),.15*params]
    x=np.zeros(6)
    for _ in range(30):
        err=residual(x)
        jac=np.column_stack([(residual(x+direction*.001)-err)/.001 for direction in np.eye(6)])
        step=np.linalg.lstsq(jac,-err,rcond=None)[0]
        x=np.clip(x+0.5*step,-.45,.45)
    return x


def apply(raw,model,params):
    d=as_density(raw);lo,hi=model['lo'],model['hi']
    return np.clip(10**(-(d+(hi-lo)*params[:3]+(d-(lo+hi)/2)*params[3:])),0,1)
