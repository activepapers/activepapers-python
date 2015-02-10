# Test specific features of ActivePapers
# coding: utf-8

import os
import numpy as np
import h5py
import tempdir
from nose.tools import raises
from activepapers.storage import ActivePaper
from activepapers.utility import ascii

def test_groups_as_items():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        group1 = paper.data.create_group('group1')
        group1.create_dataset('value', data=42)
        group2 = paper.data.create_group('group2')
        group2.mark_as_data_item()
        group2.create_dataset('array', data=np.arange(10))
        items = sorted([item.name for item in paper.iter_items()])
        assert items == ['/data/group1/value', '/data/group2']
        groups = sorted([group.name for group in paper.iter_groups()])
        assert groups == ['/data/group1']
        script = paper.create_calclet("script1",
"""
from activepapers.contents import data
x1 = data['group2']['array'][...]
x2 = data['group1']['value'][...]
data.create_dataset('sum1', data=x1+x2)
""")
        script.run()
        assert (paper.data['sum1'][...] == np.arange(42,52)).all()
        script = paper.create_calclet("script2",
"""
from activepapers.contents import data
x1 = data['/group2/array'][...]
g = data['group1']
x2 = g['/group1/value'][...]
data.create_dataset('sum2', data=x1+x2)
""")
        script.run()
        assert (paper.data['sum2'][...] == np.arange(42,52)).all()
        deps = [sorted([ascii(item.name) for item in level])
                for level in paper.dependency_hierarchy()]
        assert deps == [['/code/script1', '/code/script2',
                         '/data/group1/value', '/data/group2'],
                        ['/data/sum1', '/data/sum2']]
        deps = paper.data['sum1']._node.attrs['ACTIVE_PAPER_DEPENDENCIES']
        deps = sorted(ascii(d) for d in deps)
        assert deps == ['/code/script1',
                        '/data/group1/value', '/data/group2']
        deps = paper.data['sum2']._node.attrs['ACTIVE_PAPER_DEPENDENCIES']
        deps = sorted(ascii(d) for d in deps)
        assert deps == ['/code/script2',
                        '/data/group1/value', '/data/group2']
        paper.close()

def test_groups():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        group = paper.data.create_group('group')
        subgroup = group.create_group('subgroup')
        group['data1'] = np.arange(10)
        group['data2'] = 42
        assert sorted([g.name for g in paper.iter_groups()]) \
               == ['/data/group', '/data/group/subgroup']
        assert sorted(list(node for node in group)) \
               == ['data1', 'data2', 'subgroup']
        assert group['data1'][...].shape == (10,)
        assert group['data2'][...] == 42
        assert paper.data.parent is paper.data
        assert group.parent is paper.data
        assert group['data1'].parent is group
        assert group['data2'].parent is group
        script = paper.create_calclet("script",
"""
from activepapers.contents import data
assert data.parent is data
assert data._codelet is not None
assert data._codelet.path == '/code/script'
group = data['group']
assert group.parent is data
assert group._codelet is not None
assert group._codelet.path == '/code/script'
""")
        script.run()
        paper.close()

def test_datasets():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        dset = paper.data.create_dataset("MyDataset", (10,10,10), 'f')
        assert len(dset) == 10
        assert dset[0, 0, 0].shape == ()
        assert dset[0, 2:10, 1:9:3].shape == (8, 3)
        assert dset[:, ::2, 5].shape == (10, 5)
        assert dset[0].shape == (10, 10)
        assert dset[1, 5].shape == (10,)
        assert dset[0, ...].shape == (10, 10)
        assert dset[..., 6].shape == (10, 10)
        array = np.arange(100)
        dset = paper.data.create_dataset("MyArray", data=array)
        assert len(dset) == 100
        assert (dset[array > 50] == np.arange(51, 100)).all()
        dset[:20] = 42
        assert (dset[...] == np.array(20*[42]+list(range(20, 100)))).all()
        paper.data['a_number'] = 42
        assert paper.data['a_number'][()] == 42
        paper.close()

def test_attrs():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        group = paper.data.create_group('group')
        ds = group.create_dataset('value', data=42)
        group.mark_as_data_item()
        assert len(group.attrs) == 0
        group.attrs['foo'] = 'bar'
        assert len(group.attrs) == 1
        assert list(group.attrs) == ['foo']
        assert group.attrs['foo'] == 'bar'
        assert len(ds.attrs) == 0
        ds.attrs['foo'] = 'bar'
        assert len(ds.attrs) == 1
        assert list(ds.attrs) == ['foo']
        assert ds.attrs['foo'] == 'bar'
        paper.close()

def test_dependencies():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        paper.data.create_dataset('e', data = np.e)
        paper.data.create_dataset('pi', data = np.pi)
        script = paper.create_calclet("script",
"""
from activepapers.contents import data
import numpy as np
e = data['e'][...]
sum = data.create_dataset('sum', shape=(1,), dtype=np.float)
pi = data['pi'][...]
sum[0] = e+pi
""")
        script.run()
        deps = [ascii(item.name)
                for item in paper.iter_dependencies(paper.data['sum']._node)]
        assert sorted(deps) == ['/code/script', '/data/e', '/data/pi']
        assert not paper.is_stale(paper.data['sum']._node)
        del paper.data['e']
        paper.data['e'] = 0.
        assert paper.is_stale(paper.data['sum']._node)
        paper.close()

def test_internal_files():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        script = paper.create_calclet("write1",
"""
from activepapers.contents import open

f = open('numbers1', 'w')
for i in range(10):
    f.write(str(i)+'\\n')
f.close()
""")
        script.run()
        script = paper.create_calclet("write2",
"""
from activepapers.contents import open

with open('numbers', 'w') as f:
    for i in range(10):
        f.write(str(i)+'\\n')
""")
        script.run()
        script = paper.create_calclet("write3",
"""
from activepapers.contents import open

with open('empty', 'w') as f:
    pass
""")
        script.run()
        script = paper.create_calclet("write4",
u"""
from activepapers.contents import open

with open('utf8', 'w', encoding='utf-8') as f:
    f.write(u'déjà')
""")
        script.run()
        script = paper.create_calclet("read1",
"""
from activepapers.contents import open

f = open('numbers')
for i in range(10):
    assert f.readline().strip() == str(i)
f.close()
""")
        script.run()
        script = paper.create_calclet("read2",
"""
from activepapers.contents import open

f = open('numbers')
data = [int(line.strip()) for line in f]
f.close()
assert data == list(range(10))
""")
        script.run()
        script = paper.create_calclet("read3",
"""
from activepapers.contents import open

f = open('empty')
data = f.read()
f.close()
assert len(data) == 0
""")
        script.run()
        script = paper.create_calclet("read4",
u"""
from activepapers.contents import open

f = open('utf8', encoding='utf-8')
data = f.read()
f.close()
assert data == u'déjà'
""")
        script.run()
        script = paper.create_calclet("convert_to_binary",
"""
from activepapers.contents import open
import struct

with open('numbers') as f:
    data = [int(line.strip()) for line in f]
f = open('binary_numbers', 'wb')
f.write(struct.pack(len(data)*'h', *data))
f.close()
""")
        script.run()
        script = paper.create_calclet("read_binary",
"""
from activepapers.contents import open
import struct

f = open('binary_numbers', 'rb')
assert struct.unpack(10*'h', f.read()) == tuple(range(10))
f.close()
""")
        script.run()
        script = paper.create_calclet("write_documentation",
"""
from activepapers.contents import open_documentation

with open_documentation('hello.txt', 'w') as f:
    f.write('Hello world!\\n')
""")
        script.run()
        h = [sorted(list(ascii(item.name) for item in step))
             for step in paper.dependency_hierarchy()]
        print(h)
        assert h == [['/code/convert_to_binary',
                      '/code/read1', '/code/read2', '/code/read3',
                      '/code/read4', '/code/read_binary',
                      '/code/write1', '/code/write2', '/code/write3',
                      '/code/write4', '/code/write_documentation'],
                     ['/data/empty', '/data/numbers', '/data/numbers1',
                      '/data/utf8', '/documentation/hello.txt'],
                     ['/data/binary_numbers']]
        paper.close()

@raises(ValueError)
def test_overwrite_internal_file():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        script = paper.create_calclet("write1",
"""
from activepapers.contents import open
f = open('numbers', 'w')
for i in range(10):
    f.write(str(i)+'\\n')
f.close()
""")
        script.run()
        script = paper.create_calclet("write2",
"""
from activepapers.contents import open

with open('numbers', 'w') as f:
    for i in range(10):
        f.write(str(i)+'\\n')
""")
        script.run()
        paper.close()

@raises(ImportError)
def test_import_forbidden():
    # distutils is a forbidden module from the standard library
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, "w")
        script = paper.create_calclet("script",
"""
import distutils
""")
        script.run()
        paper.close()

def test_snapshots():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        snapshot_1 = os.path.join(t, "snapshot_1.ap")
        snapshot_2 = os.path.join(t, "snapshot_2.ap")
        paper = ActivePaper(filename, 'w')
        paper.data.create_dataset("frequency", data = 0.2)
        paper.data.create_dataset("time", data=0.1*np.arange(100))
        calc_angular = paper.create_calclet("calc_angular",
"""
from activepapers.contents import data, snapshot
import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
angular = data.create_group('angular')
angular.attrs['time'] = data['time'].ref
angular.create_dataset("time", data=data['time'].ref)
angular.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
snapshot('%s')
angular.create_dataset("cosine", data=np.cos(2.*np.pi*frequency*time))
snapshot('%s')
angular.create_dataset("tangent", data=np.tan(2.*np.pi*frequency*time))
""" % (snapshot_1, snapshot_2))
        calc_angular.run()
        paper.close()
        # Open the snapshot files to verify they are valid ActivePapers
        ActivePaper(snapshot_1, 'r').close()
        ActivePaper(snapshot_2, 'r').close()
        # Check the contents
        paper = h5py.File(filename)
        snapshot_1 = h5py.File(snapshot_1)
        snapshot_2 = h5py.File(snapshot_2)
        for item in ['/data/time', '/data/frequency', '/data/angular/sine',
                     '/code/calc_angular']:
            assert item in paper
            assert item in snapshot_1
            assert item in snapshot_2
        assert '/data/angular/cosine' in paper
        assert '/data/angular/cosine' not in snapshot_1
        assert '/data/angular/cosine' in snapshot_2
        assert '/data/angular/tangent' in paper
        assert '/data/angular/tangent' not in snapshot_1
        assert '/data/angular/tangent' not in snapshot_2
        for root in [snapshot_1, snapshot_2]:
            #time_ref = root['/data/angular/time'][()]
            #assert root[time_ref].name == '/data/time'
            time_ref = root['/data/angular'].attrs['time']
            assert root[time_ref].name == '/data/time'

def test_modified_scripts():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        script = paper.create_calclet("script",
"""
from activepapers.contents import data
data.create_dataset('foo', data=42)
group = data.create_group('group1')
group.mark_as_data_item()
group['value'] = 1
group = data.create_group('group2')
group['value'] = 2
""")
        script.run()
        items = sorted([item.name for item in paper.iter_items()])
        assert items == ['/code/script', '/data/foo',
                         '/data/group1', '/data/group2/value']
        assert (paper.data['foo'][...] == 42)
        assert (paper.data['group1/value'][...] == 1)
        assert (paper.data['group2/value'][...] == 2)
        script = paper.create_calclet("script",
"""
from activepapers.contents import data
data.create_dataset('foo', data=1)
""")
        script.run()
        items = sorted([item.name for item in paper.iter_items()])
        assert items == ['/code/script', '/data/foo']
        assert (paper.data['foo'][...] == 1)
        paper.close()

def test_dummy_datasets():
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, 'w')
        paper.data.create_dataset("frequency", data = 0.2)
        paper.data.create_dataset("time", data=0.1*np.arange(100))
        calc_angular = paper.create_calclet("calc_angular",
"""
from activepapers.contents import data, snapshot
import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
angular = data.create_group('angular')
angular.attrs['time'] = data['time'].ref
angular.create_dataset("time", data=data['time'].ref)
angular.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
""")
        calc_angular.run()
        paper.replace_by_dummy('/data/angular/sine')
        dummy = paper.data_group['angular/sine']
        assert dummy.attrs.get('ACTIVE_PAPER_GENERATING_CODELET') \
            ==  '/code/calc_angular'
        assert dummy.attrs.get('ACTIVE_PAPER_DUMMY_DATASET', False)
        passed = True
        try:
            paper.replace_by_dummy('/data/time')
        except AssertionError:
            passed = False
        assert not passed
        paper.close()
