# Test the exploration module

import os
import numpy as np
import tempdir
from activepapers.storage import ActivePaper
from activepapers import library
from activepapers.exploration import ActivePaper as ActivePaperExploration

def make_local_paper(filename):

    paper = ActivePaper(filename, "w")

    paper.data.create_dataset("frequency", data=0.2)
    paper.data.create_dataset("time", data=0.1*np.arange(100))

    paper.add_module("my_math",
"""
import numpy as np

def my_func(x):
    return np.sin(x)
""")

    paper.close()

def check_local_paper(filename):
    ap = ActivePaperExploration(filename)
    from my_math import my_func
    frequency = ap.data['frequency'][...]
    time = ap.data['time'][...]
    sine = my_func(2.*np.pi*frequency*time)
    assert (sine == np.sin(2.*np.pi*frequency*time)).all()
    ap.close()

def test_local_paper():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "test.ap")

        make_local_paper(filename)
        check_local_paper(filename)

def test_published_paper():
    with tempdir.TempDir() as t:
        library.library = [t]
        ap = ActivePaperExploration("doi:10.6084/m9.figshare.808595")
        import time_series
        ts = np.arange(10)
        assert time_series.integral(ts, 1)[-1] == 40.5
        ap.close()
