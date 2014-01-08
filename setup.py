#!/usr/bin/env python

from setuptools import setup, Command
import copy
import os
import sys

package_dir = "lib"
script_dir = "scripts"


with open('README.md') as file:
    long_description = file.read()
    long_description = long_description[:long_description.find("\n\n")]

class Dummy:
    pass
version = Dummy()
exec(open('lib/activepapers/version.py').read(), version.__dict__)

setup(name='ActivePapers.Py',
      version=version.version,
      description='Executable papers containing Python code',
      long_description=long_description,
      author='Konrad Hinsen',
      author_email='research@khinsen.fastmail.net',
      url='http://github.com/activepapers/activepapers-python',
      license='BSD',
      package_dir = {'': package_dir},
      packages=['activepapers'],
      scripts=[os.path.join(script_dir, s) for s in os.listdir(script_dir)],
      platforms=['any'],
      requires=["numpy (>=1.6)", "h5py (>=2.2)", "tempdir (>=0.6)"],
      provides=["ActivePapers.Py"],
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: BSD License",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
          "Topic :: Scientific/Engineering",
      ]
  )
