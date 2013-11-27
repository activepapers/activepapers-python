# This example illustrates how to turn a group withh everything it
# contains into a single data item for the purpose of dependency
# tracking.

from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("group_data_items.ap", "w")

script = paper.create_calclet("script1",
"""
from activepapers.contents import data
import numpy as np

numbers = data.create_group("numbers")
numbers.mark_as_data_item()
numbers.create_dataset("pi", data=np.pi)
numbers.create_dataset("e", data=np.e)
""")
script.run()

script = paper.create_calclet("script2",
"""
from activepapers.contents import data
import numpy as np

numbers = data["numbers"]
data.create_dataset("result", data=numbers["pi"][...]*numbers["e"][...])
""")
script.run()

# Check that only /data/numbers is tracked, not
# /data/numbers/pi or /data/numbers/e
for level in paper.dependency_hierarchy():
    print [item.name for item in level]

paper.close()
