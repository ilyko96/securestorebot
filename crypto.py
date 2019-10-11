import re
import hashlib

# Tests given password for strength
def is_password_weak(pwd):
	return not re.match(r'[A-Za-z0-9@#$%^&+=]{8,}', pwd)

def get_hash(pwd):
	return hashlib.sha256(pwd.encode("utf-8")).hexdigest()