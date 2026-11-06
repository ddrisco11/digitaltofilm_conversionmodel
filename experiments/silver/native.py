"""Optional compiled implementation of the reference reaction equations."""
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

_LIB = None


def available():
    return os.environ.get('FILM_NATIVE') == '1'


def develop(active, steps, bath):
    global _LIB
    if _LIB is None:
        source = Path(__file__).with_suffix('.c')
        name = 'film-' + hashlib.sha256(source.read_bytes()).hexdigest()[:16] + '.dylib'
        target = Path(tempfile.gettempdir()) / name
        if not target.exists():
            temporary = target.with_name(target.name + f'.{os.getpid()}.tmp')
            subprocess.run(['clang','-O3','-ffp-contract=off','-shared','-fPIC',
                            str(source),'-o',str(temporary)],check=True)
            temporary.replace(target)
        _LIB = ctypes.CDLL(str(target))
        pointer = np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS')
        _LIB.develop.argtypes = [pointer,pointer,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_float]
        _LIB.develop.restype = ctypes.c_int
    a=np.ascontiguousarray(active,dtype=np.float32)
    result=np.empty_like(a)
    if _LIB.develop(a,result,*a.shape,steps,bath):
        raise MemoryError('Native reaction buffer allocation failed.')
    return result
