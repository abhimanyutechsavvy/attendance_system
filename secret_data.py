import base64
import json

PASSWORD = "1910"

_ENCODED_SECRET = (
    "eyJ0YWdfaWQiOiAiMTIzNDU2Nzg5MDEyIiwgInN0dWRlbnRfaWQiOiAiUzAwMSIsICJuYW1lIjogIlN0dWRlbnQgT25lIiwgInN0b3JlZF9pbWFnZSI6ICJzdHVkZW50MS5qcGciLCAiZGVzY3JpcHRpb24iOiAiU2FtcGxlIHNpZ25hdHVyZSBzdHVkZW50IGZvciBleGFtcGxlIn0="
)


def reveal_secret(password: str):
    if str(password) != PASSWORD:
        raise ValueError("Invalid password")
    data = base64.b64decode(_ENCODED_SECRET.encode("utf-8"))
    return json.loads(data.decode("utf-8"))
