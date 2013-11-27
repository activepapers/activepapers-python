import sys
import time

# Python 2/3 compatibility issues
if sys.version_info[0] == 2:

    from activepapers.utility2 import *

else:

    from activepapers.utility3 import *

# Various small functions

def datatype(node):
    s = node.attrs.get('ACTIVE_PAPER_DATATYPE', None)
    if s is None:
        return s
    else:
        return ascii(s)

def owner(node):
    s = node.attrs.get('ACTIVE_PAPER_GENERATING_CODELET', None)
    if s is None:
        return s
    else:
        return ascii(s)

def mod_time(node):
    s = node.attrs.get('ACTIVE_PAPER_TIMESTAMP', None)
    if s is None:
        return s
    else:
        return s/1000.

def ms_since_epoch():
    return np.int64(1000.*time.time())

def timestamp(node, time=None):
    if time is None:
        time = ms_since_epoch()
    else:
        time *= 1000.
    node.attrs['ACTIVE_PAPER_TIMESTAMP'] = time

def stamp(node, ap_type, attributes):
    allowed_transformations = {'group': 'data',
                               'data': 'group',
                               'file': 'text'}
    attrs = dict(attributes)
    attrs['ACTIVE_PAPER_DATATYPE'] = ap_type
    for key, value in attrs.items():
        if value is None:
            continue
        if isstring(value):
            previous = node.attrs.get(key, None)
            if previous is None:
                node.attrs[key] = value
            else:
                if previous != value:
                    # String attributes can't change when re-stamping...
                    if key == 'ACTIVE_PAPER_DATATYPE' \
                       and allowed_transformations.get(previous) == value:
                        # ...with a few exceptions
                        node.attrs[key] = value
                    else:
                        raise ValueError("%s: %s != %s"
                                         % (key, value, previous))
        elif key == 'ACTIVE_PAPER_DEPENDENCIES':
            node.attrs.create(key, np.array(value, dtype=object),
                              shape = (len(value),), dtype=h5vstring)
        else:
            raise ValueError("unexpected key %s" % key)
    timestamp(node)

def path_in_section(path, section):
    if not isstring(path):
        raise ValueError("type %s where string is expected"
                         % str(type(path)))
    if path.startswith("/"):
        return section + path
    else:
        return path

def datapath(path):
    return path_in_section(path, "/data")

def codepath(path):
    return path_in_section(path, "/code")
