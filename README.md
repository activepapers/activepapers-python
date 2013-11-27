ActivePapers is a tool for working with executable papers, which
combine data, code, and documentation in single-file packages,
suitable for publication as supplementary material or on sites such as
[figshare](http://figshare.com).

The ActivePapers Python edition requires Python 2.7 or Python 3.2/3.3
plus the following libraries:

  - NumPy 1.6 or later (http://numpy.scipy.org/)
  - HDF5 1.8.7 or later (http://www.hdfgroup.org/HDF5/)
  - h5py 2.2 or later (http://www.h5py.org/)
  - tempdir 0.6 or later (http://pypi.python.org/pypi/tempdir/)

Installation of ActivePapers.Py:

    python setup.py install

This installs the ActivePapers Python library and
the command-line tool "aptool" for managing
ActivePapers.

For documentation, see the
[ActivePapers Web site](http://www.activepapers.org/python-edition/).

ActivePapers development takes place
[on Github](http://github.com/activepapers/activepapers-python).

Runnning the tests also requires the
[nose library](http://pypi.python.org/pypi/nose/).
Once it is installed, run

    nosetests

from this directory.
