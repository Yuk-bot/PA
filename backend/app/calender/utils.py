import os
from cryptography.fernet import Fernet


ENCRYPTION_KEY = os.getenv("CALENDER_ENCRYPTION").encode()
cipher = Fernet(ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    """Encrypt a token before storing in Firestore."""
    if not token:
        return ""
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token retrieved from Firestore."""
    if not encrypted_token:
        return ""
    return cipher.decrypt(encrypted_token.encode()).decode()