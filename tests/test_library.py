# Test file downloads

import os
import tempdir

from activepapers.storage import ActivePaper
from activepapers import library
from activepapers.utility import ascii

def test_figshare_download():
    with tempdir.TempDir() as t:
        library.library = [t]
        local_name = library.find_in_library("doi:10.6084/m9.figshare.692144")
        assert local_name == os.path.join(t, "10.6084/m9.figshare.692144.ap")
        paper = ActivePaper(local_name)
        assert ascii(paper.code_group['python-packages/immutable/__init__'].attrs['ACTIVE_PAPER_DATATYPE']) == 'module'
        paper.close()

def test_zenodo_download():
    with tempdir.TempDir() as t:
        library.library = [t]
        local_name = library.find_in_library("doi:10.5281/zenodo.7648")
        assert local_name == os.path.join(t, "10.5281/zenodo.7648.ap")
        paper = ActivePaper(local_name)
        assert ascii(paper.code_group['python-packages/mosaic/__init__'].attrs['ACTIVE_PAPER_DATATYPE']) == 'module'
        paper.close()
