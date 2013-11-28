Overview of the ActivePapers implementation
===========================================

There is currently little documentation in the code. Don't worry,
this will change.

The command-line tool is in ``scripts/aptool``. It contains just
the user interface, based on ``argparse``. The code that actually
implements the commands is in the module ``activepapers.cli``.

The ActivePapers Python library is in ``lib``. The main modules
are:

``activepapers.storage``
  Takes care of storing and retrieving data (both the contents of an
  ActivePaper and bookkeeping information) in an HDF5 file. Most
  of this module consists of the large class ``ActivePaper``.
  The class ``InternalFile`` handles the file interface to datasets
  (``activepapers.contents.open``). The class ``APNode`` handles
  references to contents in other ActivePapers.

``activepapers.execution``

  Manages the execution of codelets (classes ``Codelet``, ``Calclet``,
  and ``Importlet``), which includes restricted rights for calclets
  and access to modules stored inside an ActivePapers for both
  calclets and importlets. Tracing of dependencies during the
  execution of a codelet is also handled here (classes
  ``AttrWrapper``, ``DatasetWrapper``, and ``DataGroup``).

``activepapers.library``
  Manages the local library of ActivePapers. Downloads
  DOI references automatically if possible (which currently
  means DOIs from figshare).

``activepapers.cli``
  Contains the implementation of the subcommands of ``aptool``.

The remaining modules provide support code. Several of them are
divided into three parts: ``activepapers.X``, ``activepapers.X2``, and
``activepapers.X3``. The modules ending in ``2`` or ``3`` contain code
specific to Python 2 or Python 3. The generic one imports the right
language-specific module and perhaps adds some code that works with
both dialects.

``activepapers.url``
  A thin wrapper around the URL-related libraries, which differ between
  Python 2 and Python 3.

``activepapers.standardlib``
  Defines the subset of the standard library that is accessible from
  codelets.

``activepapers.builtins``
  Defines the subset of the builtin definitions that is accessible from
  codelets.

``activepapers.utility``
  Small functions that are used a lot in both ``activepapers.storage``
  and ``activepapers.execution``.

``activepapers.version``
  The version number of the library, stored in a single place.


Note the absence of ``activepapers.contents``, which is the module
through which codelets access the contents of an ActivePaper.  It is
created dynamically each time a codelet is run, see the class
``activepapers.execution.Codelet``.
