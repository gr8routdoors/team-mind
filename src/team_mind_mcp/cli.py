import argparse
import os
import sys
import anyio
from pathlib import Path

from team_mind_mcp.storage import StorageAdapter
from team_mind_mcp.server import MCPGateway
from team_mind_mcp.markdown import MarkdownPlugin
from team_mind_mcp.retrieval import DocumentRetrievalPlugin
from team_mind_mcp.ingestion_plugin import IngestionPlugin
from team_mind_mcp.discovery import DoctypeDiscoveryPlugin
from team_mind_mcp.feedback import FeedbackPlugin
from team_mind_mcp.lifecycle import LifecyclePlugin, load_persisted_plugins


def get_default_db_path() -> Path:
    """Returns the default database path, prioritizing the environment variable."""
    env_path = os.environ.get("TEAM_MIND_DB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Fallback to ~/.team-mind/database.sqlite
    default_dir = Path.home() / ".team-mind"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / "database.sqlite"


async def run_server(db_path: Path) -> int:
    """Initializes the database, registers plugins, and starts the MCP stdio loop."""
    print(f"Team Mind MCP Server initializing... (DB: {db_path})", file=sys.stderr)

    # Initialize Storage
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Initialize Gateway and Registry
    gateway = MCPGateway()

    # Register core plugins
    markdown_plugin = MarkdownPlugin(storage)
    retrieval_plugin = DocumentRetrievalPlugin(storage)
    ingestion_plugin = IngestionPlugin(gateway.registry, storage=storage)

    discovery_plugin = DoctypeDiscoveryPlugin(gateway.registry)
    feedback_plugin = FeedbackPlugin(storage)
    lifecycle_plugin = LifecyclePlugin(gateway.registry, storage)

    gateway.registry.register(markdown_plugin)
    gateway.registry.register(retrieval_plugin)
    gateway.registry.register(ingestion_plugin)
    gateway.registry.register(discovery_plugin)
    gateway.registry.register(feedback_plugin)
    gateway.registry.register(lifecycle_plugin)

    # Load dynamically registered plugins from persistence table
    load_persisted_plugins(storage, gateway.registry)

    # Import the stdio server here to prevent overhead on simple CLI commands
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await gateway.server.run(
            read_stream, write_stream, gateway.server.create_initialization_options()
        )

    return 0


async def run_ingest(db_path: Path, args: argparse.Namespace) -> int:
    """Executes the offline ingestion pipeline against targets."""
    print(f"Ingesting targets into {db_path}...", file=sys.stderr)

    # Initialize Storage
    storage = StorageAdapter(str(db_path))
    storage.initialize()

    # Needs Plugins initialized so pipeline has somewhere to send data
    gateway = MCPGateway()
    gateway.registry.register(MarkdownPlugin(storage))

    from team_mind_mcp.ingestion import IngestionPipeline

    pipeline = IngestionPipeline(gateway.registry, storage=storage)

    # Flatten targets if recursive
    final_uris = []

    for t in args.targets:
        target_path = Path(t).resolve()
        if target_path.is_dir():
            if args.recursive:
                # Walk the directory
                for file_path in target_path.rglob("*"):
                    if file_path.is_file():
                        final_uris.append(file_path.as_uri())
            else:
                print(
                    f"Skipping directory {target_path} since --recursive is off",
                    file=sys.stderr,
                )
        elif target_path.is_file():
            final_uris.append(target_path.as_uri())
        elif t.startswith("http://") or t.startswith("https://"):
            final_uris.append(t)
        else:
            print(f"Warning: Could not resolve target: {t}", file=sys.stderr)

    print(f"Resolved {len(final_uris)} URIs.", file=sys.stderr)
    if not final_uris:
        return 1

    bundle = await pipeline.ingest(final_uris)
    if bundle:
        print(
            f"Successfully broadcasted {len(bundle.uris)} items to plugins.",
            file=sys.stderr,
        )
        return 0
    return 1


def main() -> int:
    """Entry point for the team-mind-mcp CLI."""
    parser = argparse.ArgumentParser(description="Team Mind MCP Server & Utilities")

    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to the SQLite database (overrides TEAM_MIND_DB_PATH env var)",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Start Command
    subparsers.add_parser("start", help="Start the MCP stdio server")

    # Ingest Command
    ingest_parser = subparsers.add_parser(
        "ingest", help="Bulk ingest files or URIs into the database"
    )
    ingest_parser.add_argument(
        "targets", nargs="+", help="One or more file paths, directories, or URIs"
    )
    ingest_parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively walk directories",
    )
    ingest_parser.add_argument(
        "--exclude", type=str, action="append", help="Glob patterns to exclude"
    )

    # Temporary fallback for testing/backwards compatibility if no args provided
    if len(sys.argv) == 1:
        print("Team Mind MCP Server initializing...")
        return 0

    args = parser.parse_args()

    db_path = (
        Path(args.db_path).expanduser().resolve()
        if args.db_path
        else get_default_db_path()
    )

    if args.command == "start":
        return anyio.run(run_server, db_path)
    elif args.command == "ingest":
        return anyio.run(run_ingest, db_path, args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
