Release 0.1.2
-------------

This is a bugfix release, fixing the following issues:

 - A compatibility problem with h5py 2.3

 - Broken downloads from Zenodo, following a modification of the contents
   of the Zenodo landing pages.

 - Syntax errors in codelets were not reported correctly.


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
