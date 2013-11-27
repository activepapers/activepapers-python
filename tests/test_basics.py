# Extensive tests on a very simple ActivePaper

import collections
import os
import numpy as np
import h5py
import tempdir
from activepapers.storage import ActivePaper
from activepapers.utility import ascii


def make_simple_paper(filename):

    paper = ActivePaper(filename, "w")

    #paper.data.create_dataset("frequency", data=0.2)
    #paper.data.create_dataset("time", data=0.1*np.arange(100))

    init = paper.create_importlet("initialize",
"""
from activepapers.contents import data
import numpy as np

data['frequency'] = 0.2
data['time'] = 0.1*np.arange(100)
""")
    init.run()

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


def make_paper_with_internal_module(filename):

    paper = ActivePaper(filename, "w")

    paper.add_module("my_math",
"""
import numpy as np

def my_func(x):
    return np.sin(x)
""")

    paper.data.create_dataset("frequency", data=0.2)
    paper.data.create_dataset("time", data=0.1*np.arange(100))

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


def assert_almost_equal(x, y, tolerance):
    assert (np.fabs(np.array(x)-np.array(y)) < tolerance).all()


def assert_valid_paper(h5file):
    assert h5file.attrs['DATA_MODEL'] == ascii('active-papers-py')
    assert h5file.attrs['DATA_MODEL_MAJOR_VERSION'] == 0
    assert h5file.attrs['DATA_MODEL_MINOR_VERSION'] == 1

    for group in ['code', 'data', 'documentation']:
        assert group in h5file
        assert isinstance(h5file[group], h5py.Group)

    history = h5file['history']
    assert history.shape == (1,)
    opened = history[0]['opened']
    closed = history[0]['closed']
    def check_timestamp(name, node):
        t = node.attrs.get('ACTIVE_PAPER_TIMESTAMP', None)
        if t is not None:
            assert t >= opened
            assert t <= closed
    h5file.visititems(check_timestamp)


def check_hdf5_file(filename, ref_all_paths, ref_deps):
    h5file = h5py.File(filename, "r")
    all_paths = []
    h5file.visit(all_paths.append)
    all_paths.sort()
    assert all_paths == ref_all_paths
    assert_valid_paper(h5file)
    assert_almost_equal(h5file["data/frequency"][...], 0.2, 1.e-15)
    assert_almost_equal(h5file["data/time"][...],
                        0.1*np.arange(100),
                        1.e-15)
    assert_almost_equal(h5file["data/sine"][...],
                        np.sin(0.04*np.pi*np.arange(100)),
                        1.e-10)
    for path in ['data/frequency', 'data/sine', 'data/time']:
        assert h5file[path].attrs['ACTIVE_PAPER_DATATYPE'] == "data"
        assert h5file[path].attrs['ACTIVE_PAPER_TIMESTAMP'] > 1.e9
    for path in ['code/calc_sine']:
        assert h5file[path].attrs['ACTIVE_PAPER_DATATYPE'] == "calclet"
    deps = h5file["data/sine"].attrs['ACTIVE_PAPER_DEPENDENCIES']
    assert list(ascii(p) for p in deps) \
            == [ascii(p) for p in ref_deps]
    assert h5file["data/sine"].attrs['ACTIVE_PAPER_GENERATING_CODELET'] \
           == "/code/calc_sine"
    h5file.close()


def check_paper(filename, ref_items, ref_deps, ref_hierarchy):
    paper = ActivePaper(filename, "r")
    items = sorted([item.name for item in paper.iter_items()])
    assert items == ref_items
    items_with_deps = sorted([item.name for item in paper.iter_items()
                              if paper.has_dependencies(item)])
    assert items_with_deps == ['/data/sine']
    deps = dict((ascii(item.name),
                 sorted(list(ascii(dep.name)
                             for dep in paper.iter_dependencies(item))))
                for item in paper.iter_items())
    assert deps == ref_deps
    graph = collections.defaultdict(set)
    for item, deps in ref_deps.items():
        for d in deps:
            graph[d].add(item)
    assert graph == paper.dependency_graph()
    hierarchy = [sorted([ascii(item.name) for item in items])
                 for items in paper.dependency_hierarchy()]
    assert hierarchy == ref_hierarchy
    calclets = paper.calclets()
    assert len(calclets) == 1
    assert ascii(calclets['/code/calc_sine'].path) == '/code/calc_sine'
    paper.close()


def test_simple_paper():
    with tempdir.TempDir() as t:
        filename1 = os.path.join(t, "simple1.ap")
        filename2 = os.path.join(t, "simple2.ap")
        make_simple_paper(filename1)
        all_paths = ['README', 'code', 'code/calc_sine', 'code/initialize',
                     'data', 'data/frequency', 'data/sine', 'data/time',
                     'documentation', 'external-dependencies', 'history']
        all_items = ['/code/calc_sine', '/code/initialize', '/data/frequency',
                     '/data/sine', '/data/time']
        all_deps = {'/data/sine': ["/code/calc_sine",
                                   "/data/frequency",
                                   "/data/time"],
                    '/data/time': [],
                    '/data/frequency': [],
                    '/code/calc_sine': [],
                    '/code/initialize': []}
        sine_deps = ["/code/calc_sine",
                     "/data/frequency",
                     "/data/time"]
        hierarchy = [['/code/calc_sine', '/code/initialize',
                      '/data/frequency', '/data/time'],
                     ['/data/sine']]
        check_hdf5_file(filename1, all_paths, sine_deps)
        check_paper(filename1, all_items, all_deps, hierarchy)
        with ActivePaper(filename1, "r") as paper:
            paper.rebuild(filename2)
        check_hdf5_file(filename2, all_paths, sine_deps)
        check_paper(filename2, all_items, all_deps, hierarchy)

def test_paper_with_internal_module():
    with tempdir.TempDir() as t:
        filename1 = os.path.join(t, "im1.ap")
        filename2 = os.path.join(t, "im2.ap")
        make_paper_with_internal_module(filename1)
        all_paths = ['README', 'code', 'code/calc_sine',
                     'code/python-packages', 'code/python-packages/my_math',
                     'data', 'data/frequency', 'data/sine', 'data/time',
                     'documentation', 'external-dependencies', 'history']
        all_items = ['/code/calc_sine', '/code/python-packages/my_math',
                     '/data/frequency', '/data/sine', '/data/time']
        all_deps = {'/data/sine': ["/code/calc_sine",
                                   "/code/python-packages/my_math",
                                   "/data/frequency",
                                   "/data/time"],
                    '/data/time': [],
                    '/data/frequency': [],
                    '/code/calc_sine': [],
                    '/code/python-packages/my_math': []}
        sine_deps = ["/code/calc_sine",
                     "/code/python-packages/my_math",
                     "/data/frequency",
                     "/data/time"]
        hierarchy = [['/code/calc_sine', '/code/python-packages/my_math',
                      '/data/frequency', '/data/time'],
                     ['/data/sine']]
        check_hdf5_file(filename1, all_paths, sine_deps)
        check_paper(filename1, all_items, all_deps, hierarchy)
        with ActivePaper(filename1, "r") as paper:
            paper.rebuild(filename2)
        check_hdf5_file(filename2, all_paths, sine_deps)
        check_paper(filename2, all_items, all_deps, hierarchy)
