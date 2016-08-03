import numpy as np
import h5py

def ascii(string):
    return string

def utf8(string):
    return string.decode('utf-8')

def py_str(byte_string):
    if isinstance(byte_string, np.ndarray):
        return str(byte_string)
    else:
        assert isinstance(byte_string, str)
        return byte_string

def isstring(s):
    return isinstance(s, basestring)

def execcode(s, globals, locals=None):
    if locals is None:
        exec s in globals
    else:
        exec s in globals, locals

h5vstring = h5py.special_dtype(vlen=str)

import __builtin__ as builtins
import activepapers.builtins2 as ap_builtins

raw_input = builtins.raw_input
