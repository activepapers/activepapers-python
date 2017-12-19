Release 0.2.2
-------------

Improvements:

 - Provide a way to skip network-dependent
   tests in restricted environments
   (environment variable NO_NETWORK_ACCESS=1)

Bug fixes:

 - Prevent a crash when no home directory is defined

 - Fix a bug in accesses to nested data groups.

Release 0.2.1
-------------

Improvements:

 - Internal text files are opened as utf8 rather than ascii.

Bug fixes:

 - Prevent crashes when using Python modules in ActivePapers
   from scripts not managed by ActivePapers (using activepapers.exploration).

Release 0.2
-----------

New features:

 - Read-only access to code and data from an ActivePaper in plain
   Python scripts. This facilitates developing and testing code
   that will later be integrated into an ActivePaper.

 - Calclets have read-only access to code and to stack traces,
   allowing limited forms of introspection.

 - Internal files can be opened in binary mode.

Bug fixes:

 - Improved compatibility with recent versions of Python and h5py.

Release 0.1.4
-------------

New features:

  - Python scripts are stored using UTF-8 encoding rather than ASCII.

  - Internal files can be opened using an option "encoding" argument.
    If this is used, strings read from and written to such files
    are unicode strings.

Bug fixes:

 - A change in importlib in Python 3.4 broke the import of modules
   stored in an ActivePaper.

Release 0.1.3
-------------

New feature:

 - There is now a generic module activepapers.contents that can be
   imported from any Python script in order to provide read-only
   access to the contents of the ActivePaper that is located in the
   current directory. This is meant as an aid to codelet development.

Bug fixes:

 - Broken downloads from Zenodo, following a modification of the contents
   of the Zenodo landing pages. Actually, Zenodo went back to the
   landing page format it had before ActivePapers release 0.1.2,
   so ActivePapers also went back to how it downloaded files before.


Release 0.1.2
-------------

This is a bugfix release, fixing the following issues:

 - A compatibility problem with h5py 2.3

 - Broken downloads from Zenodo, following a modification of the contents
   of the Zenodo landing pages.

 - Syntax errors in codelets were not reported correctly.
