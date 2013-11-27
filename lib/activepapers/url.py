import sys

# Python 2/3 compatibility issues
if sys.version_info[0] == 2:

    from activepapers.url2 import *

else:

    from activepapers.url3 import *
