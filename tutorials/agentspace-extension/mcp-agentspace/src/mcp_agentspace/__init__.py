import argparse
from .server import mcp

def main():
    """MCP Agentspace: Use Agentspace to access the search engine and make search and answer queries."""
    parser = argparse.ArgumentParser(
        description="Gives you the ability to search your internal data sources."
    )
    parser.parse_args()
    mcp.run()

if __name__ == "__main__":
    main()
