import os
os.environ['ACTIVEPAPERS_LIBRARY'] = os.getcwd()

from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("ref_to_simple.ap", "w")

paper.create_data_ref("frequency", "local:simple")
paper.create_data_ref("time", "local:simple", "time")

paper.create_code_ref("calc_sine", "local:simple", "calc_sine")
paper.run_codelet('calc_sine')

paper.close()
