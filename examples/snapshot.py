from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("snapshot.ap", "w")

paper.data.create_dataset("frequency", data = 0.2)
paper.data.create_dataset("time", data=0.1*np.arange(100))

calc_angular = paper.create_calclet("calc_angular",
"""
from activepapers.contents import data, snapshot
import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
data.create_dataset("sine", data=np.sin(2.*np.pi*frequency*time))
snapshot('snapshot_1.ap')
data.create_dataset("cosine", data=np.cos(2.*np.pi*frequency*time))
snapshot('snapshot_2.ap')
data.create_dataset("tangent", data=np.tan(2.*np.pi*frequency*time))
""")
calc_angular.run()

paper.close()
