from builtins import *
from builtins import __import__
from builtins import __build_class__

# The "del exec" was removed and replaced by an equivalent operation
# in utility3 to avoid a syntax error when processing builtins by
# Python 2.
#
# del exec
del eval
del input
del open
del quit
