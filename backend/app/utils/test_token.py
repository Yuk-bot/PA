from db.firebase import firebase_auth

def get_test_token(uid: str):
    token = firebase_auth.create_custom_token(uid)
    return token.decode()

print(get_test_token("z3JIwJSE7oZbCM608bjqzC0bFps2"))