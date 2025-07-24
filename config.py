from jose import JWTError, jwt
from datetime import datetime, timedelta

# Secret key to sign JWTs. Generate a strong random string for production
SECRET_KEY = "my_ultra_secret_key"
ALGORITHM = "HS256"

# Token expiry settings
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

