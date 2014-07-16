# Test the use of references

import os

import numpy as np
import h5py
import tempdir

from activepapers.storage import ActivePaper
from activepapers.utility import ascii
from activepapers import library

def make_simple_paper(filename):

    paper = ActivePaper(filename, "w")

    paper.data.create_dataset("frequency", data=0.2)
    paper.data.create_dataset("time", data=0.1*np.arange(100))

    calc_sine = paper.create_calclet("calc_sine",
"""
from activepapers.contents import data
import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
data.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
""")
    calc_sine.run()

    paper.close()


def make_library_paper(filename):

    paper = ActivePaper(filename, "w")

    paper.add_module("my_math",
"""
import numpy as np

def my_func(x):
    return np.sin(x)
""")

    paper.close()


def make_simple_paper_with_data_refs(filename, paper_ref):

    paper = ActivePaper(filename, "w")

    paper.create_data_ref("frequency", paper_ref)
    paper.create_data_ref("time_from_ref", paper_ref, "time")

    calc_sine = paper.create_calclet("calc_sine",
"""
from activepapers.contents import data
import numpy as np

frequency = data['frequency'][...]
time = data['time_from_ref'][...]
data.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
""")
    calc_sine.run()

    paper.close()


def make_simple_paper_with_data_and_code_refs(filename, paper_ref):

    paper = ActivePaper(filename, "w")

    paper.create_data_ref("frequency", paper_ref)
    paper.create_data_ref("time", paper_ref)

    paper.create_code_ref("calc_sine", paper_ref)
    paper.run_codelet('calc_sine')

    paper.close()


def make_simple_paper_with_library_refs(filename, paper_ref):

    paper = ActivePaper(filename, "w")

    paper.data.create_dataset("frequency", data = 0.2)
    paper.data.create_dataset("time", data=0.1*np.arange(100))

    paper.create_module_ref("my_math", paper_ref)

    calc_sine = paper.create_calclet("calc_sine",
    """
from activepapers.contents import data
import numpy as np
from my_math import my_func

frequency = data['frequency'][...]
time = data['time'][...]
data.create_dataset("sine", data=my_func(2.*np.pi*frequency*time))
    """)
    calc_sine.run()

    paper.close()


def make_simple_paper_with_copies(filename, paper_ref):

    paper = ActivePaper(filename, "w")

    paper.create_copy("/data/frequency", paper_ref)
    paper.create_copy("/data/time", paper_ref)

    paper.create_copy("/code/calc_sine", paper_ref)
    paper.run_codelet('calc_sine')

    paper.close()


def assert_almost_equal(x, y, tolerance):
    assert (np.fabs(np.array(x)-np.array(y)) < tolerance).all()


def check_paper_with_refs(filename, with_name_postfix, refs, additional_items):
    time_ds_name = '/data/time_from_ref' if with_name_postfix else '/data/time'
    paper = ActivePaper(filename, "r")
    items = sorted([item.name for item in paper.iter_items()])
    assert items == sorted(['/code/calc_sine', '/data/frequency',
                            '/data/sine', time_ds_name] + additional_items)
    for item_name in refs:
        assert paper.data_group[item_name].attrs['ACTIVE_PAPER_DATATYPE'] \
                    == 'reference'
    assert_almost_equal(paper.data["sine"][...],
                        np.sin(0.04*np.pi*np.arange(100)),
                        1.e-10)
    paper.close()

def test_simple_paper_with_data_refs():
    with tempdir.TempDir() as t:
        library.library = [t]
        os.mkdir(os.path.join(t, "local"))
        filename1 = os.path.join(t, "local/simple1.ap")
        filename2 = os.path.join(t, "simple2.ap")
        make_simple_paper(filename1)
        make_simple_paper_with_data_refs(filename2, "local:simple1")
        check_paper_with_refs(filename2, True,
                              ['/data/frequency', '/data/time_from_ref'],
                              [])

def test_simple_paper_with_data_and_code_refs():
    with tempdir.TempDir() as t:
        library.library = [t]
        os.mkdir(os.path.join(t, "local"))
        filename1 = os.path.join(t, "local/simple1.ap")
        filename2 = os.path.join(t, "simple2.ap")
        make_simple_paper(filename1)
        make_simple_paper_with_data_and_code_refs(filename2, "local:simple1")
        check_paper_with_refs(filename2, False,
                              ['/data/frequency', '/data/time',
                               '/code/calc_sine'],
                              [])

def test_simple_paper_with_library_refs():
    with tempdir.TempDir() as t:
        library.library = [t]
        os.mkdir(os.path.join(t, "local"))
        filename1 = os.path.join(t, "local/library.ap")
        filename2 = os.path.join(t, "simple.ap")
        make_library_paper(filename1)
        make_simple_paper_with_library_refs(filename2, "local:library")
        check_paper_with_refs(filename2, False,
                              ['/code/python-packages/my_math'],
                              ['/code/python-packages/my_math'])


def test_copy():
    with tempdir.TempDir() as t:
        library.library = [t]
        os.mkdir(os.path.join(t, "local"))
        filename1 = os.path.join(t, "local/simple1.ap")
        filename2 = os.path.join(t, "simple2.ap")
        make_simple_paper(filename1)
        make_simple_paper_with_copies(filename2, "local:simple1")
        check_paper_with_refs(filename2, False, [], [])
        paper = ActivePaper(filename2, 'r')
        for path in ['/code/calc_sine', '/data/frequency', '/data/time']:
            item = paper.file[path]
            source = item.attrs.get('ACTIVE_PAPER_COPIED_FROM')
            assert source is not None
            paper_ref, ref_path = source
            if h5py.version.version_tuple[:2] <= (2, 2):
                paper_ref = paper_ref.flat[0]
                ref_path = ref_path.flat[0]
            assert ascii(paper_ref) == "local:simple1"
            assert ascii(ref_path) == path

