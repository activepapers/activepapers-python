# An API for opening ActivePapers read-only for exploration of their
# contents, including re-use of the code.

from activepapers.storage import ActivePaper as ActivePaperStorage
from activepapers.storage import open_paper_ref
from activepapers.utility import path_in_section

class ActivePaper(object):

    def __init__(self, file_or_ref, use_code=True):
        global _paper_for_code
        try:
            self.paper = open_paper_ref(file_or_ref)
        except ValueError:
            self.paper = ActivePaperStorage(file_or_ref, 'r')
        if use_code and ("python-packages" not in self.paper.code_group \
                         or len(self.paper.code_group["python-packages"]) == 0):
            # The paper contains no importable modules or packages.
            use_code = False
        if use_code and _paper_for_code is not None:
            raise IOError("Only one ActivePaper per process can use code.")
        self.data = self.paper.data
        self.documentation = self.paper.documentation_group
        self.code = self.paper.code_group
        try:
            self.__doc__ = self.open_documentation('README').read()
        except KeyError:
            pass
        if use_code:
            _paper_for_code = self.paper

    def close(self):
        global _paper_for_code
        if _paper_for_code is self.paper:
            _paper_for_code = None

    def _open(self, path, section, mode='r'):
        if mode not in ['r', 'rb']:
            raise ValueError("invalid mode: " + repr(mode))
        path = path_in_section(path, section)
        if not path.startswith('/'):
            path = section + '/' + path
        return self.paper.open_internal_file(path, mode, None)

    def open(self, path, mode='r'):
        return self._open(path, '/data', mode)

    def open_documentation(self, path, mode='r'):
        return self._open(path, '/documentation', mode)

    def read_code(self, file):
        return self.code[file][...].ravel()[0].decode('utf-8')

_paper_for_code = None
def _get_codelet_and_paper():
    return None, _paper_for_code
import activepapers.execution
activepapers.execution.get_codelet_and_paper = _get_codelet_and_paper
del _get_codelet_and_paper
