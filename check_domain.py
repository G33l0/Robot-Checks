#!/usr/bin/env python3
from checkers.rakuten import check

email = input("Email: ").strip()
password = input("Password: ").strip()

success, msg = check(email, password)
print(f"\nResult: {'✅' if success else '❌'} {msg}")