from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

driver = GraphDatabase.driver(
    os.environ["CONGODB_CONNECTION_URI"],
    auth=(
        os.environ["CONGODB_USERNAME"],
        os.environ["CONGODB_PASSWORD"],
    ),
)

driver.verify_connectivity()

print("Connected successfully")

driver.close()