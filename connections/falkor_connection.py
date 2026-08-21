import os

from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

URL = os.environ["FALKOR_URL"]
USERNAME = os.environ["FALKOR_USERNAME"]
PASSWORD = os.environ["FALKOR_PASSWORD"]


def main() -> None:
    client = FalkorDB.from_url(
        URL,
        username=USERNAME,
        password=PASSWORD,
    )

    graph = client.select_graph("benchmark")

    result = graph.query(
        "RETURN 1 AS result"
    )

    print("FalkorDB: Connected successfully")
    print(f"Query result: {result.result_set}")


if __name__ == "__main__":
    main()