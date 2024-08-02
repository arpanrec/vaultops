import os
from pykeepass import PyKeePass

KEEPASS_DBX = os.environ["KEEPASS_DBX"]
KEEPASS_PSW = os.environ["KEEPASS_PSW"]
KEEPASS_KEY = os.environ["KEEPASS_KEY"]

kp = PyKeePass(KEEPASS_DBX, password=KEEPASS_PSW, keyfile=KEEPASS_KEY)
# binary_id = kp.add_binary(b'Hello world')
# print(binary_id)
for idx, binary in enumerate(kp.binaries):
    print(f"Binary {idx}:")
    print(binary.title)
kp.save()
