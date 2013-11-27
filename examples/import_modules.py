from activepapers.storage import ActivePaper
import numpy as np
import os, sys

# The modules imported here are located in ../tests.
script_path = os.path.dirname(sys.argv[0])
tests_path = os.path.join(script_path, '..', 'tests')
module_path = [os.path.abspath(tests_path)]

paper = ActivePaper("import_modules.ap", "w")

# The source code of imported modules is embedded into the paper. Only
# Python source code modules can be imported, i.e. neither extension
# modules nor bytecode module (.pyc).
# The module_path parameter is a list of directories that can contain
# modules. If not specified, it defaults to sys.path
paper.import_module('foo', module_path)
paper.import_module('foo.bar', module_path)

script = paper.create_calclet("test",
"""
import foo
from foo.bar import frobnicate
assert frobnicate(foo.__version__) == '42'
""")
script.run()

paper.close()
