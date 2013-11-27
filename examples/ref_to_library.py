import os
os.environ['ACTIVEPAPERS_LIBRARY'] = os.getcwd()

from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("ref_to_library.ap", "w")

paper.data.create_dataset("frequency", data = 0.2)
paper.data.create_dataset("time", data=0.1*np.arange(100))

paper.create_module_ref("my_math", "local:internal_modules")

calc_sine = paper.create_calclet("calc_sine",
"""
from activepapers.contents import data
import numpy as np
from my_math import my_func

frequency = data['frequency'][...]
time = data['time'][...]
data.create_dataset("sine", data=my_func(2.*np.pi*frequency*time))
""")
calc_sine.run()

paper.close()
