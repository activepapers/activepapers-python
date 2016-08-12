import collections
import getpass
import imp
import importlib
import io
import itertools as it
import os
import socket
import sys
import weakref

import numpy as np
import h5py

from activepapers.utility import ascii, utf8, h5vstring, isstring, execcode, \
                                 codepath, datapath, owner, mod_time, \
                                 datatype, timestamp, stamp, ms_since_epoch
from activepapers.execution import Calclet, Importlet, DataGroup, paper_registry
from activepapers.library import find_in_library
import activepapers.version

readme_text = """
This file is an ActivePaper (Python edition).

For more information about ActivePapers see:

  http://www.activepapers.org/
"""


#
# The ActivePaper class is the only one in this library
# meant to be used directly by client code.
#

class ActivePaper(object):

    def __init__(self, filename, mode="r", dependencies=None):
        self.filename = filename
        self.file = h5py.File(filename, mode)
        self.open = True
        self.writable = False
        if mode[0] == 'r':
            assert dependencies is None
            if ascii(self.file.attrs['DATA_MODEL']) != 'active-papers-py':
                raise ValueError("File %s is not an ActivePaper" % filename)
            self.code_group = self.file["code"]
            self.data_group = self.file["data"]
            self.documentation_group = self.file["documentation"]
            self.writable = '+' in mode
            self.history = self.file['history']
            deps = self.file.get('external-dependencies/'
                                 'python-packages', None)
            if deps is None:
                self.dependencies = []
            else:
                self.dependencies = [ascii(n) for n in deps]
            for module_name in self.dependencies:
                importlib.import_module(module_name)
        elif mode[0] == 'w':
            self.file.attrs['DATA_MODEL'] = ascii('active-papers-py')
            self.file.attrs['DATA_MODEL_MAJOR_VERSION'] = 0
            self.file.attrs['DATA_MODEL_MINOR_VERSION'] = 1
            self.code_group = self.file.create_group("code")
            self.data_group = self.file.create_group("data")
            self.documentation_group = self.file.create_group("documentation")
            deps = self.file.create_group('external-dependencies')
            if dependencies is None:
                self.dependencies = []
            else:
                for module_name in dependencies:
                    assert isstring(module_name)
                    importlib.import_module(module_name)
                self.dependencies = dependencies
                ds = deps.create_dataset('python-packages',
                                         dtype = h5vstring,
                                         shape = (len(dependencies),))
                ds[:] = dependencies
            htype = np.dtype([('opened', np.int64),
                              ('closed', np.int64),
                              ('platform', h5vstring),
                              ('hostname', h5vstring),
                              ('username', h5vstring)]
                             + [(name+"_version", h5vstring)
                                for name in ['activepapers','python',
                                             'numpy', 'h5py', 'hdf5'] 
                                            + self.dependencies])
            self.history = self.file.create_dataset("history", shape=(0,),
                                                    dtype=htype,
                                                    chunks=(1,),
                                                    maxshape=(None,))
            readme = self.file.create_dataset("README",
                                              dtype=h5vstring, shape = ())
            readme[...] = readme_text
            self.writable = True

        if self.writable:
            self.update_history(close=False)

        import activepapers.utility
        self.data = DataGroup(self, None, self.data_group, ExternalCode(self))
        self.imported_modules = {}

        self._local_modules = {}

        paper_registry[self._id()] = self

    def _id(self):
        return hex(id(self))[2:]

    def update_history(self, close):
        if close:
            entry = tuple(self.history[-1])
            self.history[-1] = (entry[0], ms_since_epoch()) + entry[2:]
        else:
            self.history.resize((1+len(self.history),))
            def getversion(name):
                if hasattr(sys.modules[name], '__version__'):
                    return getattr(sys.modules[name], '__version__')
                else:
                    return 'unknown'
            self.history[-1] = (ms_since_epoch(), 0,
                                sys.platform,
                                socket.getfqdn(),
                                getpass.getuser(),
                                activepapers.__version__,
                                sys.version.split()[0],
                                np.__version__,
                                h5py.version.version,
                                h5py.version.hdf5_version) \
                               + tuple(getversion(m) for m in self.dependencies)

    def close(self):
        if self.open:
            if self.writable:
                self.update_history(close=True)
            del self._local_modules
            self.open = False
            try:
                self.file.close()
            except:
                pass
            paper_id = hex(id(self))[2:]
            try:
                del paper_registry[paper_id]
            except KeyError:
                pass

    def assert_is_open(self):
        if not self.open:
            raise ValueError("ActivePaper %s has been closed" % self.filename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def flush(self):
        self.file.flush()

    def _create_ref(self, path, paper_ref, ref_path, group, prefix):
        if ref_path is None:
            ref_path = path
        if group is None:
            group = 'file'
        if prefix is None:
            prefix = ''
        else:
            prefix += '/'
        paper = open_paper_ref(paper_ref)
        # Access the item to make sure it exists
        item = getattr(paper, group)[ref_path]
        ref_dtype = np.dtype([('paper_ref', h5vstring), ('path', h5vstring)])
        ds = getattr(self, group).require_dataset(path, shape=(),
                                                  dtype=ref_dtype)
        ds[...] = (paper_ref, prefix + ref_path)
        stamp(ds, 'reference', {})
        return ds

    def create_ref(self, path, paper_ref, ref_path=None):
        return self._create_ref(path, paper_ref, ref_path, None, None)

    def create_data_ref(self, path, paper_ref, ref_path=None):
        return self._create_ref(path, paper_ref, ref_path,
                                'data_group', '/data')

    def create_code_ref(self, path, paper_ref, ref_path=None):
        return self._create_ref(path, paper_ref, ref_path,
                                'code_group', '/code')

    def create_module_ref(self, path, paper_ref, ref_path=None):
        path = "python-packages/" + path
        if ref_path is not None:
            ref_path = "python-packages/" + ref_path
        return self.create_code_ref(path, paper_ref, ref_path)

    def create_copy(self, path, paper_ref, ref_path=None):
        if ref_path is None:
            ref_path = path
        paper = open_paper_ref(paper_ref)
        item = paper.file[ref_path]
        self.file.copy(item, path, expand_refs=True)
        copy = self.file[path]
        self._delete_dependency_attributes(copy)
        timestamp(copy, mod_time(item))
        ref_dtype = np.dtype([('paper_ref', h5vstring), ('path', h5vstring)])
        copy.attrs.create('ACTIVE_PAPER_COPIED_FROM',
                          shape=(), dtype=ref_dtype,
                          data=np.array((paper_ref, ref_path), dtype=ref_dtype))
        return copy

    def _delete_dependency_attributes(self, node):
        for attr_name in ['ACTIVE_PAPER_GENERATING_CODELET',
                          'ACTIVE_PAPER_DEPENDENCIES']:
            if attr_name in node.attrs:
                del node.attrs[attr_name]
        if isinstance(node, h5py.Group):
            for item in node:
                self._delete_dependency_attributes(node[item])

    def store_python_code(self, path, code):
        self.assert_is_open()
        if not isstring(code):
            raise TypeError("Python code must be a string (is %s)"
                            % str(type(code)))
        ds = self.code_group.require_dataset(path,
                                             dtype=h5vstring, shape = ())
        ds[...] = code.encode('utf-8')
        ds.attrs['ACTIVE_PAPER_LANGUAGE'] = "python"
        return ds

    def add_module(self, name, module_code):
        path = codepath('/'.join(['', 'python-packages'] + name.split('.')))
        ds = self.store_python_code(path, module_code)
        stamp(ds, "module", {})

    def import_module(self, name, python_path=sys.path):
        if name in self.imported_modules:
            return self.imported_modules[name]
        if '.' in name:
            # Submodule, add the underlying package first
            package, _, module = name.rpartition('.')
            path = [self.import_module(package, python_path)]
        else:
            module = name
            path = python_path
        file, filename, (suffix, mode, kind) = imp.find_module(module, path)
        if kind == imp.PKG_DIRECTORY:
            package = filename
            file = open(os.path.join(filename, '__init__.py'))
            name = name + '/__init__'
        else:
            package = None
            if file is None:
                raise ValueError("%s is not a Python module" % name)
            if kind != imp.PY_SOURCE:
                file.close()
                raise ValueError("%s is not a Python source code file"
                                 % filename)
        self.add_module(name, ascii(file.read()))
        file.close()
        self.imported_modules[name] = package
        return package

    def get_local_module(self, name):
        path = codepath('/'.join(['', 'python-packages'] + name.split('.')))
        return APNode(self.code_group).get(path, None)
        
    def create_calclet(self, path, script):
        path = codepath(path)
        if not path.startswith('/'):
            path = '/'.join([self.code_group.name, path])
        ds = self.store_python_code(path, script)
        stamp(ds, "calclet", {})
        return Calclet(self, ds)

    def create_importlet(self, path, script):
        path = codepath(path)
        if not path.startswith('/'):
            path = '/'.join([self.code_group.name, path])
        ds = self.store_python_code(path, script)
        stamp(ds, "importlet", {})
        return Importlet(self, ds)

    def run_codelet(self, path, debug=False):
        if path.startswith('/'):
            assert path.startswith('/code/')
            path = path[6:]
        node = APNode(self.code_group)[path]
        class_ = {'calclet': Calclet, 'importlet': Importlet}[datatype(node)]
        try:
            class_(self, node).run()
            return None
        except Exception:
            # TODO: preprocess traceback to show only the stack frames
            #       in the codelet.
            import traceback

            type, value, trace = sys.exc_info()
            stack = traceback.extract_tb(trace)
            del trace

            while stack:
                if stack[0][2] == 'execcode':
                    del stack[0]
                    break
                del stack[0]
            
            fstack = []
            for filename, lineno, fn_name, code in stack:
                if ':' in filename:
                    paper_id, codelet = filename.split(':')
                    paper = paper_registry.get(paper_id)
                    if paper is None:
                        paper_name = '<ActivePaper>'
                    else:
                        paper_name = '<%s>' % paper.file.filename
                    filename = ':'.join([paper_name, codelet])
                    if code is None and paper is not None:
                        script = utf8(paper.file[codelet][...].flat[0])
                        code = script.split('\n')[lineno-1]
                fstack.append((filename, lineno, fn_name, code))

            tb_text = ''.join(["Traceback (most recent call last):\n"] + \
                              traceback.format_list(fstack) + \
                              traceback.format_exception_only(type, value))
            if debug:
                sys.stderr.write(tb_text)
                import pdb
                pdb.post_mortem()
            else:
                return tb_text

    def calclets(self):
        return dict((item.name,
                     Calclet(self, item))
                    for item in self.iter_items()
                    if datatype(item) == 'calclet')

    def remove_owned_by(self, codelet):
        def owned(group):
            nodes = []
            for node in group.values():
                if owner(node) == codelet:
                    nodes.append(node.name)
                elif isinstance(node, h5py.Group) \
                   and datatype(node) != 'data':
                    nodes.extend(owned(node))
            return nodes
        for group in [self.code_group,
                      self.data_group,
                      self.documentation_group]:
            for node_name in owned(group):
                del self.file[node_name]

    def replace_by_dummy(self, item_name):
        item = self.file[item_name]
        codelet = owner(item)
        assert codelet is not None
        dtype = datatype(item)
        mtime = mod_time(item)
        deps = item.attrs.get('ACTIVE_PAPER_DEPENDENCIES')
        del self.file[item_name]
        ds = self.file.create_dataset(item_name,
                                      data=np.zeros((), dtype=np.int))
        stamp(ds, dtype,
              dict(ACTIVE_PAPER_GENERATING_CODELET=codelet,
                   ACTIVE_PAPER_DEPENDENCIES=list(deps)))
        timestamp(ds, mtime)
        ds.attrs['ACTIVE_PAPER_DUMMY_DATASET'] = True
        
    def is_dummy(self, item):
        return item.attrs.get('ACTIVE_PAPER_DUMMY_DATASET', False)

    def iter_items(self):
        """
        Iterate over the items in a paper.
        """
        def walk(group):
            for node in group.values():
                if isinstance(node, h5py.Group) \
                   and datatype(node) != 'data':
                    for gnode in walk(node):
                        yield gnode
                else:
                    yield node
        for group in [self.code_group,
                      self.data_group,
                      self.documentation_group]:
            for node in walk(group):
                yield node

    def iter_groups(self):
        """
        Iterate over the groups in a paper that are not items.
        """
        def walk(group):
            for node in group.values():
                if isinstance(node, h5py.Group) \
                   and datatype(node) != 'data':
                    yield node
                    for subnode in walk(node):
                        yield subnode
        for group in [self.code_group,
                      self.data_group,
                      self.documentation_group]:
            for node in walk(group):
                yield node

    def iter_dependencies(self, item):
        """
        Iterate over the dependencies of a given item in a paper.
        """
        if 'ACTIVE_PAPER_DEPENDENCIES' in item.attrs:
            for dep in item.attrs['ACTIVE_PAPER_DEPENDENCIES']:
                yield self.file[dep]

    def is_stale(self, item):
        t = mod_time(item)
        for dep in self.iter_dependencies(item):
            if mod_time(dep) > t:
                return True
        return False

    def external_references(self):
        def process(node, refs):
            if datatype(node) == 'reference':
                paper_ref, ref_path = node[()]
                refs[paper_ref][0].add(ref_path)
            elif 'ACTIVE_PAPER_COPIED_FROM' in node.attrs:
                source = node.attrs['ACTIVE_PAPER_COPIED_FROM']
                paper_ref, ref_path = source
                if h5py.version.version_tuple[:2] <= (2, 2):
                    # h5py 2.2 returns a wrong dtype
                    paper_ref = paper_ref.flat[0]
                    ref_path = ref_path.flat[0]
                refs[paper_ref][1].add(ref_path)
            if isinstance(node, h5py.Group):
                for item in node:
                    process(node[item], refs)
            return refs

        refs = collections.defaultdict(lambda: (set(), set()))
        for node in [self.code_group, self.data_group,
                     self.documentation_group]:
            process(node, refs)
        return refs

    def has_dependencies(self, item):
        """
        :param item: an item in a paper
        :type item: h5py.Node
        :return: True if the item has any dependencies
        :rtype: bool
        """
        return 'ACTIVE_PAPER_DEPENDENCIES' in item.attrs \
                and len(item.attrs['ACTIVE_PAPER_DEPENDENCIES']) > 0

    def dependency_graph(self):
        """
        :return: a dictionary mapping the name of each item to the
                 set of the names of the items that depend on it
        :rtype: dict
        """
        graph = collections.defaultdict(set)
        for item in it.chain(self.iter_items(), self.iter_groups()):
            for dep in self.iter_dependencies(item):
                graph[dep.name].add(item.name)
        return graph

    def dependency_hierarchy(self):
        """
        Generator yielding a sequence of sets of HDF5 paths
        such that the items in each set depend only on the items
        in the preceding sets.
        """
        known = set()
        unknown = set()
        for item in self.iter_items():
            d = (item.name,
                 frozenset(dep.name for dep in self.iter_dependencies(item)))
            if len(d[1]) > 0:
                unknown.add(d)
            else:
                known.add(d[0])
        yield set(self.file[p] for p in known)
        while len(unknown) > 0:
            next = set(p for p, d in unknown if d <= known)
            if len(next) == 0:
                raise ValueError("cyclic dependencies")
            known |= next
            unknown = set((p, d) for p, d in unknown if p not in next)
            yield set(self.file[p] for p in next)

    def rebuild(self, filename):
        """
        Rebuild all the dependent items in the paper in a new file.
        First all items without dependencies are copied to the new
        file, then all the calclets are run in the new file in the
        order determined by the dependency graph in the original file.
        """
        deps = self.dependency_hierarchy()
        with ActivePaper(filename, 'w') as clone:
            for item in next(deps):
                # Make sure all the groups in the path exist
                path = item.name.split('/')
                name = path[-1]
                groups = path[:-1]
                dest = clone.file
                while groups:
                    group_name = groups[0]
                    if len(group_name) > 0:
                        if group_name not in dest:
                            dest.create_group(group_name)
                        dest = dest[group_name]
                    del groups[0]
                clone.file.copy(item, item.name, expand_refs=True)
                timestamp(clone.file[item.name])
            for items in deps:
                calclets = set(item.attrs['ACTIVE_PAPER_GENERATING_CODELET']
                               for item in items)
                for calclet in calclets:
                    clone.run_codelet(calclet)

    def snapshot(self, filename):
        """
        Make a copy of the ActivePaper in its current state.
        This is meant to be used form inside long-running
        codelets in order to permit external monitoring of
        the progress, given that HDF5 files being written cannot
        be read simultaneously.
        """
        self.file.flush()
        clone = h5py.File(filename, 'w')
        for item in self.file:
            clone.copy(self.file[item], item, expand_refs=True)
        for attr_name in self.file.attrs:
            clone.attrs[attr_name] = self.file.attrs[attr_name]
        clone.close()

    def open_internal_file(self, path, mode='r', encoding=None, creator=None):
        # path is always relative to the root group
        if path.startswith('/'):
            path = path[1:]
        if not path.startswith('data/') \
           and not path.startswith('documentation/'):
            raise IOError((13, "Permission denied: '%s'" % path))
        if creator is None:
            creator = ExternalCode(self)
        if mode[0] in ['r', 'a']:
            ds = self.file[path]
        elif mode[0] == 'w':
            test = self.file.get(path, None)
            if test is not None:
                if not creator.owns(test):
                    raise ValueError("%s trying to overwrite data"
                                     " created by %s"
                                     % (creator.path, owner(test)))
                del self.file[path]
            ds = self.file.create_dataset(
                       path, shape = (0,), dtype = np.uint8,
                       chunks = (100,), maxshape = (None,))
        else:
            raise ValueError("unknown file mode %s" % mode)
        return InternalFile(ds, mode, encoding)


#
# A dummy replacement that emulates the interface of Calclet.
#

class ExternalCode(object):

    def __init__(self, paper):
        self.paper = paper
        self.path = None

    def add_dependency(self, dependency):
        pass

    def dependency_attributes(self):
        return {}

    def owns(self, node):
        # Pretend to be the owner of everything
        return True


#
# A Python file interface for byte array datasets
#

class InternalFile(io.IOBase):

    def __init__(self, ds, mode, encoding=None):
        self._ds = ds
        self._mode = mode
        self._encoding = encoding
        self._position = 0
        self._closed = False
        self._binary = 'b' in mode
        self._get_attributes = lambda: {}
        self._stamp()

    def readable(self):
        return True

    def writable(self):
        return self._mode[0] == 'w' or '+' in self._mode

    @property
    def closed(self):
        return self._closed

    @property
    def mode(self):
        return self._mode

    @property
    def name(self):
        return self._ds.name

    def _check_if_open(self):
        if self._closed:
            raise ValueError("file has been closed")

    def _convert(self, data):
        if self._binary:
            return data
        elif self._encoding is not None:
            return data.decode(self._encoding)
        else:
            return ascii(data)

    def _set_attribute_callback(self, callback):
        self._get_attributes = callback

    def _stamp(self):
        if self.writable():
            stamp(self._ds, "file", self._get_attributes())

    def close(self):
        self._closed = True
        self._stamp()

    def flush(self):
        self._check_if_open()

    def isatty(self):
        return False

    def __next__(self):
        self._check_if_open()
        if self._position == len(self._ds):
            raise StopIteration
        return self.readline()
    next = __next__ # for Python 2

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def read(self, size=None):
        self._check_if_open()
        if size is None:
            size = len(self._ds)-self._position
        if size == 0:
            return ''
        else:
            new_position = self._position + size
            data = self._ds[self._position:new_position]
            self._position = new_position
            return self._convert(data.tostring())

    def readline(self, size=None):
        self._check_if_open()
        remaining = len(self._ds) - self._position
        if remaining == 0:
            return self._convert('')
        for l in range(min(100, remaining), remaining+100, 100):
            data = self._ds[self._position:self._position+l]
            eols = np.nonzero(data == 10)[0]
            if len(eols) > 0:
                n = eols[0]+1
                self._position += n
                return self._convert(data[:n].tostring())
        self._position = len(self._ds)
        return self._convert(data.tostring())

    def readlines(self, sizehint=None):
        self._check_if_open()
        return list(line for line in self)

    def seek(self, offset, whence=os.SEEK_SET):
        self._check_if_open()
        file_length = len(self._ds)
        if whence == os.SEEK_SET:
            self._position = offset
        elif whence == os.SEEK_CUR:
            self._position += offset
        elif whence == os.SEEK_END:
            self._position = file_length + offset
        self._position = max(0, min(file_length, self._position))

    def tell(self):
        self._check_if_open()
        return self._position

    def truncate(self, size=None):
        self._check_if_open()
        if size is None:
            size = self._position
        self._ds.resize((size,))
        self._stamp()

    def write(self, string):
        self._check_if_open()
        if self._mode[0] == 'r':
            raise IOError("File not open for writing")
        if not string:
            # HDF5 crashes when trying to write a zero-length
            # slice, so this must be handled as a special case.
            return
        if self._encoding is not None:
            string = string.encode(self._encoding)
        new_position = self._position + len(string)
        if new_position > len(self._ds):
            self._ds.resize((new_position,))
        self._ds[self._position:new_position] = \
                np.fromstring(string, dtype=np.uint8)
        self._position = new_position
        self._stamp()

    def writelines(self, strings):
        self._check_if_open()
        for line in strings:
            self.write(line)


#
# A wrapper for nodes that works across references
#

class APNode(object):

    def __init__(self, h5node, name = None):
        self._h5node = h5node
        self.name = h5node.name if name is None else name

    def is_group(self):
        return isinstance(self._h5node, h5py.Group)

    def __contains__(self, item):
        return item in self._h5node

    def __getitem__(self, item):
        if isinstance(self._h5node, h5py.Group):
            path = item.split('/')
            if path[0] == '':
                node = APNode(self._h5node.file)
                path = path[1:]
            else:
                node = self
            for item in path:
                node = node._getitem(item)
            return node
        else:
            return self._h5node[item]

    def get(self, item, default):
        try:
            return self[item]
        except:
            return default

    def _getitem(self, item):
        node = self._h5node
        if datatype(node) == 'reference':
            _, node = dereference(node)
        node = node[item]
        if datatype(node) == 'reference':
            _, node = dereference(node)
        name = self.name
        if not name.endswith('/'): name += '/'
        name += item
        return APNode(node, name)

    def __getattr__(self, attrname):
        return getattr(self._h5node, attrname)

    def in_paper(self, paper):
        return paper.file.id == self._h5node.file.id

#
# A global dictionary mapping paper_refs to papers.
# Each entry disappears when no reference to the paper remains.
#
_papers = weakref.WeakValueDictionary()

# # Close all open referenced papers at interpreter exit,
# # in order to prevent "murdered identifiers" in h5py.
# def _cleanup():
#     for paper in activepapers.storage._papers.values():
#         paper.close()

# import atexit
# atexit.register(_cleanup)
# del atexit

#
# Dereference a reference node
#
def dereference(ref_node):
    assert datatype(ref_node) == 'reference'
    paper_ref, path = ref_node[()]
    paper = open_paper_ref(ascii(paper_ref))
    return paper, paper.file[path]

#
# Open a paper given its reference
#
def open_paper_ref(paper_ref):
    if paper_ref in _papers:
        return _papers[paper_ref]
    paper = ActivePaper(find_in_library(paper_ref), "r")
    _papers[paper_ref] = paper
    return paper
