# An API for opening ActivePapers read-only for exploration of their
# contents, including re-use of the code.

from activepapers.storage import ActivePaper as ActivePaperStorage
from activepapers.storage import open_paper_ref
from activepapers.utility import path_in_section

class ActivePaper(object):

    def __init__(self, file_or_ref, use_code=False):
        global _paper_for_code
        if use_code and _paper_for_code is not None:
            raise IOError("Only one ActivePaper per process can use code.")
        try:
            self.paper = open_paper_ref(file_or_ref)
            self.data = self.paper.data
            self.documentation = self.paper.documentation_group
            self.code = self.paper.code_group
        except IOError:
            self.paper = ActivePaperStorage(file_or_ref, 'r')
        try:
            self.__doc__ = self.open_documentation('README').read()
        except KeyError:
            pass
        if use_code:
            _paper_for_code = self.paper
            
    def _open(self, path, section):
        path = path_in_section(path, section)
        if not path.startswith('/'):
            path = section + '/' + path
        return self.paper.open_internal_file(path, 'r', None)

    def open(self, path):
        return self._open(path, '/data')

    def open_documentation(self, path):
        return self._open(path, '/documentation')

_paper_for_code = None
def _get_codelet_and_paper():
    return None, _paper_for_code
import activepapers.execution
activepapers.execution.get_codelet_and_paper = _get_codelet_and_paper
del _get_codelet_and_paper
