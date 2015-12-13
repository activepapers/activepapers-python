# Command line interface implementation

import fnmatch
import itertools as it
import os
import re
import subprocess
import sys
import time
import tempdir

import numpy
import h5py

import activepapers.storage
from activepapers.utility import ascii, datatype, mod_time, stamp, \
                                 timestamp, raw_input

class CLIExit(Exception):
    pass

def get_paper(input_filename):
    if input_filename is not None:
        return input_filename
    apfiles = [fn for fn in os.listdir('.') if fn.endswith('.ap')]
    if len(apfiles) == 1:
        return apfiles[0]
    sys.stderr.write("no filename given and ")
    if apfiles:
        sys.stderr.write("%d HDF5 files in current directory\n" % len(apfiles))
    else:
        sys.stderr.write("no HDF5 file in current directory\n")
    raise CLIExit


#
# Support for checkin/checkout/extract
#

extractable_types = ['calclet', 'importlet', 'module', 'file', 'text']

file_extensions = {('calclet', 'python'): '.py',
                   ('importlet', 'python'): '.py',
                   ('module', 'python'): '.py',
                   ('file', None): '',
                   ('text', 'HTML'): '.html',
                   ('text', 'LaTeX'): '.tex',
                   ('text', 'markdown'): '.md',
                   ('text', 'reStructuredText'): '.rst',
                   ('text', None): '.txt'}

file_languages = dict((_ext, _l)
                      for (_t, _l), _ext in file_extensions.items())

def extract_to_file(paper, item, file=None, filename=None, directory=None):
    if file is None:
        if filename is not None:
            filename = os.path.abspath(filename)
        if directory is not None:
            directory = os.path.abspath(directory)
        if filename is not None and directory is not None:
            if not filename.startswith(directory):
                raise ValueError("% not in directory %s"
                                 % (filename, directory))
        if filename is None:
            item_name = item.name.split('/')[1:]
            filename = os.path.join(directory, *item_name)
            if '.' not in item_name[-1]:
                # Add a file extension using some heuristics
                language = item.attrs.get('ACTIVE_PAPER_LANGUAGE', None)
                filename += file_extensions.get((datatype(item), language), '')
        directory, _ = os.path.split(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        file = open(filename, 'wb')
        close = True
    else:
        # If a file object is given, no other file specification is allowed
        assert filename is None
        assert directory is None
        close = False
    dt = datatype(item)
    if dt in ['file', 'text']:
        internal = activepapers.storage.InternalFile(item, 'rb')
        file.write(internal.read())
    elif dt in extractable_types:
        file.write(item[...].flat[0])
    else:
        raise ValueError("cannot extract dataset %s of type %s"
                         % (item.name, dt))
    if close:
        file.close()
        mtime = mod_time(item)
        if mtime:
            os.utime(filename, (mtime, mtime))
    return filename

def update_from_file(paper, filename, type=None,
                     force_update=False, dry_run=False,
                     dataset_name=None, create_new=True):
    if not os.path.exists(filename):
        raise ValueError("File %s not found" % filename)
    mtime = os.path.getmtime(filename)
    basename = filename
    ext = ''
    if dataset_name is not None:
        item = paper.file.get(dataset_name, None)
        if item is not None:
            basename = item.name
    else:
        item = paper.file.get(basename, None)
        if item is None:
            basename, ext = os.path.splitext(filename)
            item = paper.file.get(basename, None)
    language = file_languages.get(ext, None)
    if item is None:
        if not create_new:
            return
        # Create new item
        if type is None:
            raise ValueError("Datatype required to create new item %s"
                             % basename)
        if type in ['calclet', 'importlet', 'module']:
            if not basename.startswith('code/'):
                raise ValueError("Items of type %s must be"
                                 " in the code section"
                                 % type)
            if language != 'python':
                raise ValueError("Items of type %s must be Python code"
                                 % type)
            if type == 'module' and \
               not basename.startswith('code/python-packages/'):
                raise ValueError("Items of type %s must be in"
                                 "code/python-packages"
                                 % type)
        elif type == 'file':
            if not basename.startswith('data/') \
               and not basename.startswith('documentation/'):
                raise ValueError("Items of type %s must be"
                                 " in the data or documentation section"
                                 % type)
            basename += ext
        elif type == 'text':
            if not basename.startswith('documentation/'):
                raise ValueError("Items of type %s must be"
                                 " in the documentation section"
                                 % type)
    else:
        # Update existing item
        if mtime <= mod_time(item) and not force_update:
            if dry_run:
                sys.stdout.write("Skip %s: file %s is not newer\n"
                                 % (item.name, filename))
            return
        if type is not None and type != datatype(item):
            raise ValueError("Cannot change datatype %s to %s"
                              % (datatype(item), type))
        if type is None:
            type = datatype(item)
        if language is None:
            language = item.attrs.get('ACTIVE_PAPER_LANGUAGE', None)
        if dry_run:
            sys.stdout.write("Delete %s\n" % item.name)
        else:
            del item.parent[item.name.split('/')[-1]]
    if dry_run:
        fulltype = type if language is None else '/'.join((type, language))
        sys.stdout.write("Create item %s of type %s from file %s\n"
                         % (basename, fulltype, filename))
    else:
        if type in ['calclet', 'importlet', 'module']:
            code = open(filename, 'rb').read().decode('utf-8')
            item = paper.store_python_code(basename[5:], code)
            stamp(item, type, {})
            timestamp(item, mtime)
        elif type in ['file', 'text']:
            f = paper.open_internal_file(basename, 'w')
            f.write(open(filename, 'rb').read())
            f.close()
            stamp(f._ds, type, {'ACTIVE_PAPER_LANGUAGE': language})
            timestamp(f._ds, mtime)

def directory_pattern(pattern):
    if pattern[-1] in "?*/":
        return None
    return pattern + "/*"

def process_patterns(patterns):
    if patterns is None:
        return None
    patterns = sum([(p, directory_pattern(p)) for p in patterns], ())
    patterns = [re.compile(fnmatch.translate(p))
                for p in patterns
                if p is not None]
    return patterns

#
#  Command handlers called from argparse
#

def create(paper, d=None):
    if paper is None:
        sys.stderr.write("no paper given\n")
        raise CLIExit
    paper = activepapers.storage.ActivePaper(paper, 'w', d)
    paper.close()

def ls(paper, long, type, pattern):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r')
    pattern = process_patterns(pattern)
    for item in paper.iter_items():
        name = item.name[1:] # remove initial slash
        dtype = datatype(item)
        if item.attrs.get('ACTIVE_PAPER_DUMMY_DATASET', False):
            dtype = 'dummy'
        if pattern and \
           not any(p.match(name) for p in pattern):
            continue
        if type is not None and dtype != type:
            continue
        if long:
            t = item.attrs.get('ACTIVE_PAPER_TIMESTAMP', None)
            if t is None:
                sys.stdout.write(21*" ")
            else:
                sys.stdout.write(time.strftime("%Y-%m-%d/%H:%M:%S  ",
                                               time.localtime(t/1000.)))
            field_len = len("importlet ")  # the longest data type name
            sys.stdout.write((dtype + field_len*" ")[:field_len])
            sys.stdout.write('*' if paper.is_stale(item) else ' ')
        sys.stdout.write(name)
        sys.stdout.write('\n')
    paper.close()

def rm(paper, force, pattern):
    paper_name = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper_name, 'r')
    deps = paper.dependency_graph()
    pattern = process_patterns(pattern)
    if not pattern:
        return
    names = set()
    for item in it.chain(paper.iter_items(), paper.iter_groups()):
        if any(p.match(item.name[1:]) for p in pattern):
            names.add(item.name)
    paper.close()
    if not names:
        return
    while True:
        new_names = set()
        for name in names:
            for dep in deps[name]:
                new_names.add(dep)
        if new_names - names:
            names |= new_names
        else:
            break
    names = sorted(names)
    if not force:
        for name in names:
            sys.stdout.write(name + '\n')
        while True:
            reply = raw_input("Delete ? (y/n) ")
            if reply in "yn":
                break
        if reply == 'n':
            return
    paper = activepapers.storage.ActivePaper(paper_name, 'r+')
    most_recent_group = None
    for name in names:
        if most_recent_group and name.startswith(most_recent_group):
            continue
        if isinstance(paper.file[name], h5py.Group):
            most_recent_group = name
        try:
            del paper.file[name]
        except:
            sys.stderr.write("Can't delete %s\n" % name)
    paper.close()

def dummy(paper, force, pattern):
    paper_name = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper_name, 'r')
    deps = paper.dependency_graph()
    pattern = process_patterns(pattern)
    if not pattern:
        return
    names = set()
    for item in paper.iter_items():
        if any(p.match(item.name[1:]) for p in pattern):
            names.add(item.name)
    paper.close()
    if not names:
        return
    names = sorted(names)
    if not force:
        for name in names:
            sys.stdout.write(name + '\n')
        while True:
            reply = raw_input("Replace by dummy datasets? (y/n) ")
            if reply in "yn":
                break
        if reply == 'n':
            return
    paper = activepapers.storage.ActivePaper(paper_name, 'r+')
    for name in names:
        try:
            paper.replace_by_dummy(name)
        except:
            sys.stderr.write("Can't replace %s by dummy\n" % name)
            raise
    paper.close()

def set_(paper, dataset, expr):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+')
    value = eval(expr, numpy.__dict__, {})
    try:
        del paper.data[dataset]
    except KeyError:
        pass
    paper.data[dataset] = value
    paper.close()

def group(paper, group_name):
    if group_name.startswith('/'):
        group_name = group_name[1:]
    top_level = group_name.split('/')[0]
    if top_level not in ['code', 'data', 'documentation']:
        sys.stderr.write("invalid group name %s\n" % group_name)
        raise CLIExit
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+')
    paper.file.create_group(group_name)
    paper.close()

def extract(paper, dataset, filename):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r')
    ds = paper.file[dataset]
    try:
        if filename == '-':
            extract_to_file(paper, ds, file=sys.stdout)
        else:
            extract_to_file(paper, ds, filename=filename)
    except ValueError as exc:
        sys.stderr.write(exc.args[0] + '\n')
        raise CLIExit

def _script(paper, dataset, filename, run, create_method):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+')
    script = open(filename).read()
    codelet = getattr(paper, create_method)(dataset, script)
    if run:
        codelet.run()
    paper.close()

def calclet(paper, dataset, filename, run):
    _script(paper, dataset, filename, run, "create_calclet")

def importlet(paper, dataset, filename, run):
    _script(paper, dataset, filename, run, "create_importlet")

def import_module(paper, module):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+')
    paper.import_module(module)
    paper.close()

def run(paper, codelet, debug, profile, checkin):
    paper = get_paper(paper)
    with activepapers.storage.ActivePaper(paper, 'r+') as paper:
        if checkin:
            for root, dirs, files in os.walk('code'):
                for f in files:
                    filename = os.path.join(root, f)
                    try:
                        update_from_file(paper, filename)
                    except ValueError as exc:
                        sys.stderr.write(exc.args[0] + '\n')
        try:
            if profile is None:
                exc = paper.run_codelet(codelet, debug)
            else:
                import cProfile, pstats
                pr = cProfile.Profile()
                pr.enable()
                exc = paper.run_codelet(codelet, debug)
                pr.disable()
                ps = pstats.Stats(pr)
                ps.dump_stats(profile)
        except KeyError:
            sys.stderr.write("Codelet %s does not exist\n" % codelet)
            raise CLIExit
        if exc is not None:
            sys.stderr.write(exc)

def _find_calclet_for_dummy_or_stale_item(paper_name):
    paper = activepapers.storage.ActivePaper(paper_name, 'r')
    deps = paper.dependency_hierarchy()
    next(deps) # the first set has no dependencies
    calclet = None
    item_name = None
    for item_set in deps:
        for item in item_set:
            if paper.is_dummy(item) or paper.is_stale(item):
                item_name = item.name
                calclet = item.attrs['ACTIVE_PAPER_GENERATING_CODELET']
                break
        # We must del item_set to prevent h5py from crashing when the
        # file is closed. Presumably there are HDF5 handles being freed
        # as a consequence of the del.
        del item_set
        if calclet is not None:
            break
    paper.close()
    return calclet, item_name

def update(paper, verbose):
    paper_name = get_paper(paper)
    while True:
        calclet, item_name = _find_calclet_for_dummy_or_stale_item(paper_name)
        if calclet is None:
            break
        if verbose:
            sys.stdout.write("Dataset %s is stale or dummy, running %s\n"
                             % (item_name, calclet))
            sys.stdout.flush()
        paper = activepapers.storage.ActivePaper(paper_name, 'r+')
        paper.run_codelet(calclet)
        paper.close()

def checkin(paper, type, file, force, dry_run):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+')
    cwd = os.path.abspath(os.getcwd())
    for filename in file:
        filename = os.path.abspath(filename)
        if not filename.startswith(cwd):
            sys.stderr.write("File %s is not in the working directory\n"
                             % filename)
            raise CLIExit
        filename = filename[len(cwd)+1:]

        def update(filename):
            try:
                update_from_file(paper, filename, type, force, dry_run)
            except ValueError as exc:
                sys.stderr.write(exc.args[0] + '\n')

        if os.path.isdir(filename):
            for root, dirs, files in os.walk(filename):
                for f in files:
                    update(os.path.join(root, f))
        else:
            update(filename)

    paper.close()

def checkout(paper, type, pattern, dry_run):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r')
    pattern = process_patterns(pattern)
    for item in paper.iter_items():
        name = item.name[1:] # remove initial slash
        dtype = datatype(item)
        if pattern and \
           not any(p.match(name) for p in pattern):
            continue
        if type is not None and dtype != type:
            continue
        try:
            extract_to_file(paper, item, directory=os.getcwd())
        except ValueError:
            sys.stderr.write("Skipping %s: data type %s not extractable\n"
                             % (item.name, datatype(item)))
    paper.close()

def ln(paper, reference, name):
    ref_parts = reference.split(':')
    if len(ref_parts) != 3:
        sys.stderr.write('Invalid reference %s\n' % reference)
        raise CLIExit
    ref_type, ref_name, ref_path = ref_parts
    with activepapers.storage.ActivePaper(get_paper(paper), 'r+') as paper:
        if ref_path == '':
            ref_path = None
        paper.create_ref(name, ref_type + ':' + ref_name, ref_path)
    
def cp(paper, reference, name):
    ref_parts = reference.split(':')
    if len(ref_parts) != 3:
        sys.stderr.write('Invalid reference %s\n' % reference)
        raise CLIExit
    ref_type, ref_name, ref_path = ref_parts
    with activepapers.storage.ActivePaper(get_paper(paper), 'r+') as paper:
        if ref_path == '':
            ref_path = None
        paper.create_copy(name, ref_type + ':' + ref_name, ref_path)

def refs(paper, verbose):
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r')
    refs = paper.external_references()
    paper.close()
    sorted_refs = sorted(refs.keys())
    for ref in sorted_refs:
        sys.stdout.write(ref.decode('utf-8') + '\n')
        if verbose:
            links, copies = refs[ref]
            if links:
                sys.stdout.write("  links:\n")
                for l in links:
                    sys.stdout.write("    %s\n" % l)
            if copies:
                sys.stdout.write("  copies:\n")
                for c in copies:
                    sys.stdout.write("    %s\n" % c)

def edit(paper, dataset):
    editor = os.getenv("EDITOR", "vi")
    paper_name = get_paper(paper)
    with tempdir.TempDir() as t:
        paper = activepapers.storage.ActivePaper(paper_name, 'r')
        ds = paper.file[dataset]
        try:
            filename = extract_to_file(paper, ds, directory=str(t))
        except ValueError as exc:
            sys.stderr.write(exc.args[0] + '\n')
            raise CLIExit
        finally:
            paper.close()
        ret = subprocess.call([editor, filename])
        if ret == 0:
            paper = activepapers.storage.ActivePaper(paper_name, 'r+')
            try:
                update_from_file(paper, filename,
                                 dataset_name=dataset, create_new=False)
            finally:
                paper.close()

def console(paper, modify):
    import code
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+' if modify else 'r')
    data = paper.data
    environment = {'data': paper.data}
    code.interact(banner = "ActivePapers interactive console",
                  local = environment)
    paper.close()

def ipython(paper, modify):
    import IPython
    paper = get_paper(paper)
    paper = activepapers.storage.ActivePaper(paper, 'r+' if modify else 'r')
    data = paper.data
    IPython.embed()
    paper.close()
