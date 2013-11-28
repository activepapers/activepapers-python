Writing codelets
================

Scripts inside an ActivePaper are called "codelets", which come in two
varieties: calclets and importlets. As their names indicate, they are
ideally small, using code from modules to do most of the work. The
only difference between calclets and importlets is that calclets run
in a restricted environment, whereas importlets have full access to
the computer's resources: files, installed Python modules, network,
etc. Calclets represent the reproducible part of an ActivePaper's
computations.  Importlets most probably don't work on anyone else's
computer, and thus should be used only when absolutely necessary. The
main reason for using an importlet, as its name suggests, is importing
data from the outside world into an ActivePaper.

Restricted environment execution
--------------------------------

Calclets are run in a modified Python environment, which includes a
subset of the Python standard library, the NumPy library, the
ActivePapers library, and all Python modules stored inside the
ActivePaper, directly or through references. The subset of the
standard library includes everything needed for computation, but no
I/O, network access, or platform-specific
modules. ActivePapers-compliant I/O is provided through the
ActivePapers library, as explained below.

Since Python does not provide secure restricted environments, the
restrictions are really no more than encouragements to respect the
rules. You can get around all of them with some ingenuity, but this
documentation won't tell you how. Keep this in mind when running other
people's code: if you have resons to suspect malicious intents, look
at the code before running it.

Importlets are run in an augmented environment. They have access to
everything a standard Python script can use, but they can (and must,
in order to be useful) also use the I/O functionality from the
ActivePaper library to write data to the ActivePaper.

Accessing additional Python modules
-----------------------------------

When a calclet tries to use a module that is not part of the restricted
environment described above, ActivePapers aborts with an error message.
The right solution for that problem is to include that module's source
code in the ActivePaper, or to package it as a separate ActivePaper and
access it through a reference.

Unfortunately, this is not always possible. The most common technical
obstacle are extension modules, which are not allowed in an
ActivePaper. Licensing restrictions can also prevent re-publication in
an ActivePaper. For such situations, ActivePapers provides a way to
extend the restricted execution environment by additional modules and
packages. This is done when the ActivePaper is created using ``aptool``,
using the ``-d`` option to ``aptool create``.

Note that adding a module to the restricted execution environment
means that anyone working with your ActivePaper will have to have
install the additional modules and packages, in versions compatible to
the ones you used.


I/O in ActivePapers
-------------------

The module ``activepapers.contents`` provides two ways to read and write
data: a file-like approach, and direct dataset access using the
`h5py <http://www.h5py.org/>`_ library.

File-like I/O is the easiest to use, and since it is very compatible
to the Python library's file protocol, it can be used with many
existing Python libraries. Here is a simple example:

    from activepapers.contents import open

    with open('numbers', 'w') as f:
        for i in range(10):
            f.write(str(i)+'\\n')

You can use the ``open`` function just like you would use the standard
Python ``open`` function, the only difference being that you pass it a
dataset name rather than a filename. The above example creates the
dataset ``/data/numbers``, i.e. the dataset names are relative to the
ActivePaper's `data` group.

There is also ``open_documentation``, which works in the same way but
accesses datasets relative to the top-level ``documentation`` group.
Datasets in this group are meant for human consumption, not for
input to other calclets.

Direct use of HDF5 datasets through ``h5py`` provides much more
powerful data management options, in particular for large binary
datasets.  The following example stores the same data as the preceding
one, but as a binary dataset:

    from activepapers.contents import data
    import numpy as np
    data['numbers] = np.arange(10)

The ``data`` object in the module ``activepapers.contents`` behaves
much like a group object from ``h5py``, the only difference being that
all data accesses are tracked for creating the dependency graph in the
ActivePaper. Most code based on ``h5py`` should work in an
ActivePaper, with the exception of code that tests objects for being
instances of specific h5py classes.
