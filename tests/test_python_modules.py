import os
import sys
import tempdir
from nose.tools import raises
from activepapers.storage import ActivePaper
from activepapers.utility import isstring

def make_paper(filename):
    paper = ActivePaper(filename, "w")
    paper.import_module('foo')
    paper.import_module('foo.bar')
    script = paper.create_calclet("test",
"""
from activepapers.contents import data
import foo
from foo.bar import frobnicate
data['result'] = frobnicate(2)
assert frobnicate(foo.__version__) == '42'
""")
    script.run()
    paper.close()

def assert_is_python_module(node):
    assert node.attrs.get('ACTIVE_PAPER_DATATYPE', None) == 'module'
    assert node.attrs.get('ACTIVE_PAPER_LANGUAGE', None) == 'python'
    
def check_paper(filename):
    paper = ActivePaper(filename, "r")
    items = sorted([item.name for item in paper.iter_items()])
    assert items == ["/code/python-packages/foo/__init__",
                     "/code/python-packages/foo/bar",
                     "/code/test",
                     "/data/result"]
    deps = [sorted(item.name for item in level)
            for level in paper.dependency_hierarchy()]
    assert deps == [['/code/python-packages/foo/__init__',
                     '/code/python-packages/foo/bar',
                     '/code/test'],
                    ['/data/result']]
    for path in ['foo/__init__', 'foo/bar']:
        node = paper.code_group['python-packages'][path]
        assert_is_python_module(node)
    paper.close()

def test_simple_paper():
    with tempdir.TempDir() as t:
        filename1 = os.path.join(t, "paper1.ap")
        filename2 = os.path.join(t, "paper2.ap")
        make_paper(filename1)
        check_paper(filename1)
        with ActivePaper(filename1, "r") as paper:
            paper.rebuild(filename2)
        check_paper(filename2)

def make_paper_with_module(filename, value):
    paper = ActivePaper(filename, "w")
    paper.add_module("some_values",
"""
a_value = %d
""" % value)
    script = paper.create_calclet("test",
"""
from activepapers.contents import data
from some_values import a_value
data['a_value'] = a_value
""")
    script.run()
    paper.close()

def check_paper_with_module(filename, value):
    paper = ActivePaper(filename, "r")
    assert paper.data['a_value'][...] == value
    paper.close()

def test_module_paper():
    with tempdir.TempDir() as t:
        filename1 = os.path.join(t, "paper1.ap")
        filename2 = os.path.join(t, "paper2.ap")
        make_paper_with_module(filename1, 42)
        check_paper_with_module(filename1, 42)
        make_paper_with_module(filename2, 0)
        check_paper_with_module(filename2, 0)

@raises(ValueError)
def test_import_math():
    # math is an extension module, so this should fail
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, "w")
        paper.import_module('math')
        paper.close()

@raises(ImportError)
def test_import_ctypes():
    # ctypes is not in the "allowed module" list, so this should fail
    with tempdir.TempDir() as t:
        filename = os.path.join(t, "paper.ap")
        paper = ActivePaper(filename, "w")
        script = paper.create_calclet("test",
"""
import ctypes
""")
        script.run()
        paper.close()
