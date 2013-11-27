from activepapers.storage import ActivePaper
import numpy as np

paper = ActivePaper("internal_files.ap", "w")

script = paper.create_calclet("write",
"""
from activepapers.contents import open

with open('numbers', 'w') as f:
    for i in range(10):
        f.write(str(i)+'\\n')
""")
script.run()

script = paper.create_calclet("read1",
"""
from activepapers.contents import open

f = open('numbers')
for i in range(10):
    assert f.readline().strip() == str(i)
f.close()
""")
script.run()

script = paper.create_calclet("read2",
"""
from activepapers.contents import open

f = open('numbers')
data = [int(line.strip()) for line in f]
f.close()
assert data == list(range(10))
""")
script.run()

script = paper.create_calclet("convert_to_binary",
"""
from activepapers.contents import open
import struct

with open('numbers') as f:
    data = [int(line.strip()) for line in f]
f = open('binary_numbers', 'wb')
f.write(struct.pack(len(data)*'h', *data))
f.close()
""")
script.run()

script = paper.create_calclet("read_binary",
"""
from activepapers.contents import open
import struct

f = open('binary_numbers', 'rb')
assert struct.unpack(10*'h', f.read()) == tuple(range(10))
f.close()
""")
script.run()

paper.close()
