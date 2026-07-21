from checkers.topcashback import check

email = "melissameckley2019@gmail.com"
password = "Password@2026"

success, msg = check(email, password)
print(f"Success: {success}")
print(f"Message: {msg}")