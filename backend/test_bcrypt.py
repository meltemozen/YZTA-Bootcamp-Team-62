import logging

import bcrypt

logging.basicConfig(level=logging.DEBUG)

print("bcrypt version:", bcrypt.__version__)

try:
    password = "test1234"
    # Generate salt and hash the password (needs bytes)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    print("Hashed:", hashed.decode("utf-8"))

    # Check the password
    is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed)
    print("Is valid:", is_valid)
except Exception:
    import traceback
    traceback.print_exc()
