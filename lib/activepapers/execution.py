import imp
import collections
import os
import sys
import threading
import traceback
import weakref
import logging

import h5py
import numpy as np

import activepapers.utility
from activepapers.utility import ascii, utf8, isstring, execcode, \
                                 codepath, datapath, path_in_section, owner, \
                                 datatype, language, \
                                 timestamp, stamp, ms_since_epoch
import activepapers.standardlib

#
# A codelet is a Python script inside a paper.
#
# Codelets come in several varieties:
#
#  - Calclets can only access datasets inside the paper.
#    Their computations are reproducible.
#
#  - Importlets create datasets in the paper based on external resources.
#    Their results are not reproducible, and in general they are not
#    executable in a different environment. They are stored as documentation
#    and for manual re-execution.
#

class Codelet(object):

    def __init__(self, paper, node):
        self.paper = paper
        self.node = node
        self._dependencies = None
        assert node.name.startswith('/code/')
        self.path = node.name

    def dependency_attributes(self):
        if self._dependencies is None:
            return {'ACTIVE_PAPER_GENERATING_CODELET': self.path}
        else:
            deps = list(self._dependencies)
            deps.append(ascii(self.path))
            deps.sort()
            return {'ACTIVE_PAPER_GENERATING_CODELET': self.path,
                    'ACTIVE_PAPER_DEPENDENCIES': deps}

    def add_dependency(self, dependency):
        pass

    def owns(self, node):
        return owner(node) == self.path

    def _open_file(self, path, mode, encoding, section):
        if path.startswith(os.path.expanduser('~')):
            # Catch obvious attempts to access real files
            # rather than internal ones.
            raise IOError((13, "Permission denied: '%s'" % path))
        path = path_in_section(path, section)
        if not path.startswith('/'):
            path = section + '/' + path
        f = self.paper.open_internal_file(path, mode, encoding, self)
        f._set_attribute_callback(self.dependency_attributes)
        if mode[0] == 'r':
            self.add_dependency(f._ds.name)
        return f

    def open_data_file(self, path, mode='r', encoding=None):
        return self._open_file(path, mode, encoding, '/data')

    def open_documentation_file(self, path, mode='r', encoding=None):
        return self._open_file(path, mode, encoding, '/documentation')

    def exception_traceback(self):
        from traceback import extract_tb, print_exc
        import sys
        tb = sys.exc_info()[2]
        node, line, fn_name, _ = extract_tb(tb, limit=2)[1]
        paper_id, path = node.split(':')
        return CodeFile(self.paper, self.paper.file[path]), line, fn_name

    def _run(self, environment):
        logging.info("Running %s %s"
                     % (self.__class__.__name__.lower(), self.path))
        self.paper.remove_owned_by(self.path)
        # A string uniquely identifying the paper from which the
        # calclet is called. Used in Importer.
        script = utf8(self.node[...].flat[0])
        script = compile(script, ':'.join([self.paper._id(), self.path]), 'exec')
        self._contents_module = imp.new_module('activepapers.contents')
        self._contents_module.data = DataGroup(self.paper, None,
                                               self.paper.data_group, self)
        self._contents_module.code = CodeGroup(self.paper,
                                               self.paper.code_group)
        self._contents_module.open = self.open_data_file
        self._contents_module.open_documentation = self.open_documentation_file
        self._contents_module.snapshot = self.paper.snapshot
        self._contents_module.exception_traceback = self.exception_traceback

        # The remaining part of this method is not thread-safe because
        # of the way the global state in sys.modules is modified.
        with codelet_lock:
            try:
                codelet_registry[(self.paper._id(), self.path)] = self
                for name, module in self.paper._local_modules.items():
                    assert name not in sys.modules
                    sys.modules[name] = module
                sys.modules['activepapers.contents'] = self._contents_module
                execcode(script, environment)
            finally:
                del codelet_registry[(self.paper._id(), self.path)]
                self._contents_module = None
                if 'activepapers.contents' in sys.modules:
                    del sys.modules['activepapers.contents']
                for name, module in self.paper._local_modules.items():
                    del sys.modules[name]

codelet_lock = threading.Lock()

#
# Importlets are run in the normal Python environment, with in
# addition access to the special module activepapers.contents.
#
# All data generation is traced during importlet execution in order to
# build the dependency graph.
#
# Importlets are be allowed to read dataset except those they
# generated themselves. This is not enforced at the moment.
#

class Importlet(Codelet):

    def run(self):
        environment = {'__builtins__': activepapers.utility.builtins.__dict__}
        self._run(environment)

    def track_and_check_import(self, module_name):
        return

#
# Calclets are run in a restricted execution environment:
#  - many items removed from __builtins__
#  - modified __import__ for tracking and verifying imports
#  - an import hook for accessing modules stored in the paper
#
# All data access and data generation is traced during calclet
# execution in order to build the dependency graph.
#

class Calclet(Codelet):

    def run(self):
        self._dependencies = set()
        environment = {'__builtins__':
                       activepapers.utility.ap_builtins.__dict__}
        self._run(environment)

    def add_dependency(self, dependency):
        assert isinstance(self._dependencies, set)
        self._dependencies.add(ascii(dependency))

    def track_and_check_import(self, module_name):
        if module_name == 'activepapers.contents':
            return
        node = self.paper.get_local_module(module_name)
        if node is None:
            top_level = module_name.split('.')[0]
            if top_level not in self.paper.dependencies \
               and top_level not in activepapers.standardlib.allowed_modules \
               and top_level not in ['numpy', 'h5py']:
                raise ImportError("import of %s not allowed" % module_name)
        else:
            if datatype(node) != "module":
                node = node.get("__init__", None)
            if node is not None and node.in_paper(self.paper):
                self.add_dependency(node.name)


#
# The attrs attribute of datasets and groups is wrapped
# by a class that makes the attributes used by ACTIVE_PAPERS
# invisible to calclet code.
#

class AttrWrapper(collections.MutableMapping):

    def __init__(self, node):
        self._node = node

    @classmethod
    def forbidden(cls, key):
        return isstring(key) and key.startswith('ACTIVE_PAPER')

    def __len__(self):
        return len([k for k in self._node.attrs
                    if not AttrWrapper.forbidden(k)])

    def __iter__(self):
        for k in self._node.attrs:
            if not AttrWrapper.forbidden(k):
                yield k

    def __contains__(self, item):
        if AttrWrapper.forbidden(item):
            return False
        return item in self._node.attrs

    def __getitem__(self, item):
        if AttrWrapper.forbidden(item):
            raise KeyError(item)
        return self._node.attrs[item]

    def __setitem__(self, item, value):
        if AttrWrapper.forbidden(item):
            raise ValueError(item)
        self._node.attrs[item] = value

    def __delitem__(self, item):
        if AttrWrapper.forbidden(item):
            raise KeyError(item)
        del self._node.attrs[item]


#
# Datasets are wrapped by a class that traces all accesses for
# building the dependency graph.
#

class DatasetWrapper(object):

    def __init__(self, parent, ds, codelet):
        self._parent = parent
        self._node = ds
        self._codelet = codelet
        self.attrs = AttrWrapper(ds)
        self.ref = ds.ref

    @property
    def parent(self):
        return self._parent

    def __len__(self):
        return len(self._node)

    def __getitem__(self, item):
        return self._node[item]

    def __setitem__(self, item, value):
        self._node[item] = value
        stamp(self._node, "data", self._codelet.dependency_attributes())

    def __getattr__(self, attr):
        return getattr(self._node, attr)

    def read_direct(dest, source_sel=None, dest_sel=None):
        return self._node.read_direct(dest, source_sel, dest_sel)

    def resize(self, size, axis=None):
        self._node.resize(size, axis)
        stamp(self._node, "data", self._codelet.dependency_attributes())

    def write_direct(source, source_sel=None, dest_sel=None):
        self._node.write_direct(source, source_sel, dest_sel)
        stamp(self._node, "data", self._codelet.dependency_attributes())

    def __repr__(self):
        codelet = owner(self._node)
        if codelet is None:
            owned = ""
        else:
            owned = " generated by %s" % codelet
        lines = ["Dataset %s%s" % (self._node.name, owned)]
        nelems = np.product(self._node.shape)
        if nelems < 100:
            lines.append(str(self._node[...]))
        else:
            lines.append("shape %s, dtype %s"
                         % (repr(self._node.shape), str(self._node.dtype)))
        return "\n".join(lines)

#
# DataGroup is a wrapper class for the "data" group in a paper.
# The wrapper traces access and creation of subgroups and datasets
# for building the dependency graph. It also maintains the illusion
# that the data subgroup is all there is in the HDF5 file.
#

class DataGroup(object):

    def __init__(self, paper, parent, h5group, codelet, data_item=None):
        self._paper = paper
        self._parent = parent if parent is not None else self
        self._node = h5group
        self._codelet = codelet
        self._data_item = data_item
        if self._data_item is None and datatype(h5group) == "data":
            self._data_item = self
        self.attrs = AttrWrapper(h5group)
        self.ref = h5group.ref
        self.name = h5group.name

    @property
    def parent(self):
        return self._parent

    def _wrap_and_track_dependencies(self, node):
        ap_type = datatype(node)
        if ap_type == 'reference':
            from activepapers.storage import dereference
            paper, node = dereference(node)
            if isinstance(node, h5py.Group):
                node = DataGroup(paper, None, node, None, None)
            else:
                node = DatasetWrapper(None, node, None)
        else:
            if self._codelet is not None:
                if ap_type is not None and ap_type != "group":
                    self._codelet.add_dependency(node.name
                                                 if self._data_item is None
                                                 else self._data_item.name)
                codelet = owner(node)
                if codelet is not None \
                   and datatype(self._node[codelet]) == "calclet":
                    self._codelet.add_dependency(codelet)
            if isinstance(node, h5py.Group):
                node = DataGroup(self._paper, self, node,
                                 self._codelet, self._data_item)
            else:
                node = DatasetWrapper(self, node, self._codelet)
        return node

    def _stamp_new_node(self, node, ap_type):
        if self._data_item:
            stamp(self._data_item._node, "data",
                  self._codelet.dependency_attributes())
        else:
            stamp(node, ap_type, self._codelet.dependency_attributes())

    def __len__(self):
        return len(self._node)

    def __iter__(self):
        for x in self._node:
            yield x

    def __getitem__(self, path_or_ref):
        if isstring(path_or_ref):
            path = datapath(path_or_ref)
        else:
            path = self._node[path_or_ref].name
            assert path.startswith('/data')
        path = path.split('/')
        if path[0] == '':
            # datapath() ensures that path must start with
            # ['', 'data'] in this case. Move up the parent
            # chain to the root of the /data hierarchy.
            path = path[2:]
            node = self
            while node is not node.parent:
                node = node.parent
        else:
            node = self
        for element in path:
            node = node._wrap_and_track_dependencies(node._node[element])
        return node

    def get(self, path, default=None):
        try:
            return self[path]
        except KeyError:
            return default

    def __setitem__(self, path, value):
        path = datapath(path)
        needs_stamp = False
        if isinstance(value, (DataGroup, DatasetWrapper)):
            value = value._node
        else:
            needs_stamp = True
        self._node[path] = value
        if needs_stamp:
            node = self._node[path]
            stamp(node, "data", self._codelet.dependency_attributes())

    def __delitem__(self, path):
        test = self._node[datapath(path)]
        if owner(test) == self._codelet.path:
            del self._node[datapath(path)]
        else:
            raise ValueError("%s trying to remove data created by %s"
                             % (str(self._codelet.path), str(owner(test))))

    def create_group(self, path):
        group = self._node.create_group(datapath(path))
        self._stamp_new_node(group, "group")
        return DataGroup(self._paper, self, group,
                         self._codelet, self._data_item)

    def require_group(self, path):
        group = self._node.require_group(datapath(path))
        self._stamp_new_node(group, "group")
        return DataGroup(self._paper, self, group,
                         self._codelet, self._data_item)

    def mark_as_data_item(self):
        stamp(self._node, "data", self._codelet.dependency_attributes())
        self._data_item = self

    def create_dataset(self, path, *args, **kwargs):
        ds = self._node.create_dataset(datapath(path), *args, **kwargs)
        self._stamp_new_node(ds, "data")
        return DatasetWrapper(self, ds, self._codelet)

    def require_dataset(self, path, *args, **kwargs):
        ds = self._node.require_dataset(datapath(path), *args, **kwargs)
        self._stamp_new_node(ds, "data")
        return DatasetWrapper(self, ds, self._codelet)

    def visit(self, func):
        self._node.visit(func)

    def visititems(self, func):
        self._node.visititems(func)

    def copy(source, dest, name=None):
        raise NotImplementedError("not yet implemented")

    def flush(self):
        self._paper.flush()

    def __repr__(self):
        codelet = owner(self._node)
        if codelet is None:
            owned = ""
        else:
            owned = " generated by %s" % codelet
        items = list(self._node)
        if not items:
            lines = ["Empty group %s%s" % (self._node.name, owned)]
        else:
            lines = ["Group %s%s containing" % (self._node.name, owned)]
            lines.extend("   "+i for i in items)
        return "\n".join(lines)

#
# CodeGroup is a wrapper class for the "code" group in a paper.
# The wrapper provide read-only access to codelets and modules.
#

class CodeGroup(object):

    def __init__(self, paper, node):
        self._paper = paper
        self._node = node

    def __len__(self):
        return len(self._node)

    def __iter__(self):
        for x in self._node:
            yield x

    def __getitem__(self, path_or_ref):
        if isstring(path_or_ref):
            path = codepath(path_or_ref)
        else:
            path = self._node[path_or_ref].name
            assert path.startswith('/code')
        node = self._node[path]
        if isinstance(node, h5py.Group):
            return CodeGroup(self._paper, node)
        else:
            return CodeFile(self._paper, node)

    def __repr__(self):
        return "<CodeGroup %s>" % self._node.name

class CodeFile(object):

    def __init__(self, paper, node):
        self._paper = paper
        self._node = node
        self.type = datatype(node)
        self.language = language(node)
        self.name = node.name
        self.code = utf8(node[...].flat[0])

    def __repr__(self):
        return "<%s %s (%s)>" % (self.type, self.name, self.language)

#
# Initialize a paper registry that permits finding a paper
# object through a unique id stored in the codelet names,
# and a codelet registry for retrieving active codelets.
#

paper_registry = weakref.WeakValueDictionary()
codelet_registry = weakref.WeakValueDictionary()

#
# Identify calls from inside a codelet in order to apply
# the codelet-specific import rules.
#

def get_codelet_and_paper():
    """
    :returns: the codelet from which this function was called,
              and the paper containing it. Both values are None
              if there is no codelet in the call chain.
    """
    # Get the name of the source code file of the current
    # module, which is also the module containing the Codelet class.
    this_module = __file__
    if os.path.splitext(this_module)[1] in ['.pyc', '.pyo']:
            this_module = this_module[:-1]
    # Get call stack minus the last entry, which is the
    # method find_module itself.
    stack = traceback.extract_stack()[:-1]
    # Look for the entry corresponding to Codelet.run()
    in_codelet = False
    for filename, line_no, fn_name, command in stack:
        if filename == this_module \
           and command == "execcode(script, environment)":
            in_codelet = True
    if not in_codelet:
        return None, None
    # Look for an entry corresponding to codelet code.
    # Extract its paper_id and use it to look up the paper
    # in the registry.
    for item in stack:
        module_ref = item[0].split(':')
        if len(module_ref) != 2:
            # module_ref is a real filename
            continue
        paper_id, codelet = module_ref
        if not codelet.startswith('/code'):
            # module_ref is something other than a paper:codelet combo
            return None, None
        return codelet_registry.get((paper_id, codelet), None), \
               paper_registry.get(paper_id, None)
    return None, None

#
# Install an importer for accessing Python modules inside papers
#

class Importer(object):

    def find_module(self, fullname, path=None):
        codelet, paper = get_codelet_and_paper()
        if paper is None:
            return None
        node = paper.get_local_module(fullname)
        if node is None:
            # No corresponding node found
            return None
        is_package = False
        if node.is_group():
            # Node is a group, so this should be a package
            if '__init__' not in node:
                # Not a package
                return None
            is_package = True
            node = node['__init__']
        if datatype(node) != "module" \
           or ascii(node.attrs.get("ACTIVE_PAPER_LANGUAGE", "")) != "python":
            # Node found but is not a Python module
            return None
        return ModuleLoader(paper, fullname, node, is_package)


class ModuleLoader(object):

    def __init__(self, paper, fullname, node, is_package):
        self.paper = paper
        self.fullname = fullname
        self.node = node
        # Python 3.4 has special treatment for loaders that
        # have an attribute 'is_package'.
        self._is_package = is_package

    def load_module(self, fullname):
        assert fullname == self.fullname
        if fullname in sys.modules:
            module = sys.modules[fullname]
            loader = getattr(module, '__loader__', None)
            if isinstance(loader, ModuleLoader):
                assert loader.paper is self.paper
            return module
        code = compile(ascii(self.node[...].flat[0]),
                       ':'.join([self.paper._id(), self.node.name]),
                       'exec')
        module = imp.new_module(fullname)
        module.__file__ = os.path.abspath(self.node.file.filename) + ':' + \
                          self.node.name
        module.__loader__ = self
        if self._is_package:
            module.__path__ = []
            module.__package__ = fullname
        else:
            module.__package__ = fullname.rpartition('.')[0]
        sys.modules[fullname] = module
        self.paper._local_modules[fullname] = module
        try:
            execcode(code, module.__dict__)
        except:
            del sys.modules[fullname]
            del self.paper._local_modules[fullname]
            raise
        return module

sys.meta_path.insert(0, Importer())

#
# Install an import hook for intercepting imports from codelets
#

standard__import__ = __import__
def ap__import__(*args, **kwargs):
    codelet, paper = get_codelet_and_paper()
    if codelet is not None:
        codelet.track_and_check_import(args[0])
    return standard__import__(*args, **kwargs)
activepapers.utility.ap_builtins.__import__ = ap__import__
