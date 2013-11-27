import sys

if sys.version_info[0] == 2:

    from activepapers.standardlib2 import *

else:

    from activepapers.standardlib3 import *

del sys
