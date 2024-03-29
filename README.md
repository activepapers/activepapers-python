As of 2024, this project is archived and unmaintained. While is has achieved its
mission of demonstrating that unifying computational reproducibility and
provenance tracking is doable and useful, it has also demonstrated that Python
is not a suitable platform to build on for reproducible research. Breaking
changes at all layers of the software stack are too frequent. The ActivePapers
framework itself (this project) uses an API that was removed in Python 3.9,
and while it can be updated with reasonable effort, there is little point
in doing so: Published ActivePapers cannot be expected to work with a current
Python stack for more than a year.

If you came here because you wish to re-run a published ActivePaper, the best
advice I can give is to use [Guix](https://guix.gnu.org/) with its
[time-machine](https://guix.gnu.org/manual/en/html_node/Invoking-guix-time_002dmachine.html)
feature to re-create a Python stack close in time to the paper you are working with.
The ActivePapers infrastructre is packaged in Guix as `python-activepapers`.

If you came here to learn about reproducible research practices, the best advice
I can give is not to use Python.

The following text is the README from 2018.

<br>

ActivePapers is a tool for working with executable papers, which
combine data, code, and documentation in single-file packages,
suitable for publication as supplementary material or on sites such as
[figshare](http://figshare.com).

The ActivePapers Python edition requires Python 2.7 or Python 3.3 to 3.5.
It also relies on the following libraries:

  - NumPy 1.6 or later (http://numpy.scipy.org/)
  - HDF5 1.8.7 or later (http://www.hdfgroup.org/HDF5/)
  - h5py 2.2 or later (http://www.h5py.org/)
  - tempdir 0.6 or later (http://pypi.python.org/pypi/tempdir/)

Installation of ActivePapers.Py:

    python setup.py install

This installs the ActivePapers Python library and the command-line
tool "aptool" for managing ActivePapers.

For documentation, see the
[ActivePapers Web site](http://www.activepapers.org/python-edition/).

ActivePapers development takes place
[on Github](http://github.com/activepapers/activepapers-python).

Runnning the tests also requires the [tempdir](https://pypi.python.org/pypi/tempdir/) library and either the 
[nose](http://pypi.python.org/pypi/nose/) or the [pytest](http://pytest.org) testing framework. The recommended way to run the tests is

```
cd tests
./run_all_tests.sh nosetests
```
or
```
cd tests
./run_all_tests.sh py.test
```

This launches the test runner on each test script individually. The simpler approach of simply running `nosetests` or `py.test` in directory `tests` leads to a few test failures because the testing framework's import handling conflicts with the implementation of internal modules in ActivePapers.
