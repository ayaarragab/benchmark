import os
import base64
from arango import ArangoClient
from dotenv import load_dotenv

load_dotenv()

encodedCA = os.environ["ARANGO_ENCODED_CA"]
arango_username = os.environ["ARANGO_USERNAME"]
arango_password = os.environ["ARANGO_PASSWORD"]
arango_host = os.environ["ARANGO_HOST"]

if not encodedCA or not arango_password:
    print("Error: Missing ARANGO_ENCODED_CA or ARANGO_PASSWORD in .env file")
    exit(1)

try:
    file_content = base64.b64decode(encodedCA)
    with open("cert_file.crt", "w+") as f:
        f.write(file_content.decode("utf-8"))
except Exception as e:
    print(f"Certificate Error: {str(e)}")
    exit(1)

client = ArangoClient(
    hosts=arango_host, 
    verify_override="cert_file.crt"
)

sys_db = client.db("_system", username=arango_username, password=arango_password)

print("ArangoDB connected successfully. Version:", sys_db.version())