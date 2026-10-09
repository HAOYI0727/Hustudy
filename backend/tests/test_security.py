from app.core.security import create_access_token, hash_password, read_access_token, verify_password
def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple"); assert encoded != "correct horse battery staple"; assert verify_password("correct horse battery staple", encoded); assert not verify_password("wrong", encoded)
def test_access_token_rejects_tampering():
    token = create_access_token("user-1", "secret", 5); assert read_access_token(token, "secret") == "user-1"; assert read_access_token(token + "x", "secret") is None
