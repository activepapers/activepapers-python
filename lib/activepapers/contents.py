# This module is not used by code running inside an ActivePaper,
# because the ActivePaper runtime system (execution.py) creates
# a specific module on the fly. This generic module
# is used when activepapers.contents is imported from a
# standard Python script. It is meant to be facilitate
# development of codelets for ActivePaper in a standard
# Python development environment.


# Locate the (hopefully only) ActivePaper in the current directory
import os
apfiles = [fn for fn in os.listdir('.') if fn.endswith('.ap')]
if len(apfiles) != 1:
    raise IOError("directory contains %s ActivePapers" % len(apfiles))
del os

# Open the paper read-only
from activepapers.storage import ActivePaper
_paper = ActivePaper(apfiles[0], 'r')
del apfiles
del ActivePaper

# Emulate the internal activepapers.contents module
data = _paper.data

def _open(filename, mode='r'):
    from activepapers.utility import path_in_section
    section = '/data'
    path = path_in_section(path, section)
    if not path.startswith('/'):
        path = section + '/' + path
    assert mode == 'r'
    return _paper.open_internal_file(path, 'r', None)

def open(filename, mode='r'):
    return _open(filename, mode, '/data')

def open_documentation(filename, mode='r'):
    return _open(filename, mode, '/documentation')

# Make the code in the ActivePapers importable
import activepapers.execution
def _get_codelet_and_paper():
    return None, _paper
activepapers.execution.get_codelet_and_paper = _get_codelet_and_paper
del _get_codelet_and_paper
