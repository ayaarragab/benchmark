import os
from gqlalchemy import Memgraph
from dotenv import load_dotenv

load_dotenv()


def hello_memgraph(host: str, port: int, username: str, password: str):
    connection = Memgraph(host, port, username, password, encrypted=True)
    results = connection.execute_and_fetch(
        'CREATE (n:FirstNode { message: "Hello Memgraph from Python!" }) RETURN n.message AS message'
    )
    print("Created node with message:", next(results)["message"])

if __name__ == "__main__":
    hello_memgraph(os.environ["MEMGRAPH_HOST"], os.environ["MEMGRAPH_PORT"], os.environ["MEMGRAPH_USERNAME"], os.environ["MEMGRAPH_PASSWORD"])