import numpy as np
import h5py

def ascii(string):
    if isinstance(string, bytes):
        return bytes.decode(string, 'ASCII')
    return string

def utf8(string):
    if isinstance(string, bytes):
        return bytes.decode(string, 'utf-8')
    return string

def py_str(byte_string):
    if isinstance(byte_string, np.ndarray):
        byte_string = bytes(byte_string)
    assert isinstance(byte_string, bytes)
    return byte_string.decode('ASCII')

def isstring(s):
    return isinstance(s, str)

def execstring(s, globals, locals=None):
    if locals is None:
        exec(s, globals)
    else:
        exec(s, globals, locals)

h5vstring = h5py.special_dtype(vlen=bytes)

import builtins
import activepapers.builtins3 as ap_builtins
# Replace the "del exec" in builtins3 by something that's not a
# syntax error under Python 2.
del ap_builtins.__dict__['exec']

raw_input = builtins.input
