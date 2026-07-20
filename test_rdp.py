# test_rdp.py (placed in project root)
from checkers.rdparena import check

email = "issamsoboh96@gmail.com"
password = "Msi249336*"

success, msg = check(email, password)
print(f"Success: {success}")
print(f"Message: {msg}")