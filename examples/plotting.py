from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("plotting.ap", "w",
                    dependencies = ["matplotlib"])

paper.data.create_dataset("frequency", data = 0.2)
paper.data.create_dataset("time", data=0.1*np.arange(100))

plot_sine = paper.create_calclet("plot_sine",
"""
from activepapers.contents import open, data
import matplotlib
# Make matplotlib ignore the user's .matplotlibrc
matplotlib.rcdefaults()
# Use the SVG backend. Must be done *before* importing pyplot.
matplotlib.use('SVG')
import matplotlib.pyplot as plt

import numpy as np

frequency = data['frequency'][...]
time = data['time'][...]
sine = np.sin(2.*np.pi*frequency*time)

plt.plot(time, sine)
# Save plot to a file, which is simulated by a HDF5 byte array
with open('sine_plot.svg', 'w') as output:
    plt.savefig(output)
""")
plot_sine.run()

paper.close()
