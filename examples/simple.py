from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("simple.ap", "w")

paper.data.create_dataset("frequency", data = 0.2)
paper.data.create_dataset("time", data=0.1*np.arange(100))

calc_sine = paper.create_calclet("calc_sine",
"""
from activepapers.contents import data
import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
data.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
""")
calc_sine.run()

paper.close()
