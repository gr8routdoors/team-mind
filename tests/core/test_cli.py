"""
BDD tests for STORY-006 and STORY-007
CLI Configuration & Environment Variables, and Bulk Ingestion Subcommand
"""
import pytest
import subprocess
import os
from pathlib import Path

# Provide tests for AC-001, AC-002, AC-003 (STORY-006)
# Testing AC-001
def test_cli_global_db_path_argument():
    """
    AC-001: Global Database Path Configuration
    """
    # Assuming the CLI correctly outputs "Ingesting targets into <DB_PATH>..." 
    # when we specify a custom db path with a dry-run/fake target
    
    custom_db_path = "/tmp/team-mind-custom.sqlite"
    
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp", "--db-path", custom_db_path, "ingest", "fake-target"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"}
    )
    
    # Check stderr as the print is directed to sys.stderr in our cli.py
    assert custom_db_path in result.stderr

def test_cli_environment_variable_fallback():
    """
    AC-002: Environment Variable Fallback 
    """
    custom_db_path = "/tmp/team-mind-env.sqlite"
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["TEAM_MIND_DB_PATH"] = custom_db_path
    
    # Run WITHOUT --db-path explicit
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp", "ingest", "fake-target"],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert custom_db_path in result.stderr

def test_cli_default_fallback_path():
    """
    AC-003: Default Fallback Path
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    if "TEAM_MIND_DB_PATH" in env:
        del env["TEAM_MIND_DB_PATH"]
        
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp", "ingest", "fake-target"],
        capture_output=True,
        text=True,
        env=env
    )
    
    default_path = str(Path.home() / ".team-mind" / "database.sqlite")
    assert default_path in result.stderr


# Tests for AC-001, AC-002, AC-003 (STORY-007)
def test_cli_ingest_remote_uri():
    """
    STORY-007, AC-003: Remote URI Pass-through
    """
    remote_uri = "https://example.com/api.md"
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp", "ingest", remote_uri],
        capture_output=True,
        text=True,
        env=env
    )
    
    # It attempts to broadcast the URI, should log "Successfully broadcasted 1 items"
    # because ResourceResolver will successfully pass HTTP URIs
    assert "Successfully broadcasted 1 items" in result.stderr


def test_cli_ingest_recursive_directory(tmp_path):
    """
    STORY-007, AC-002: Recursive Directory Resolution
    """
    # Create temp nested structure
    nested_dir = tmp_path / "subdir"
    nested_dir.mkdir()
    
    f1 = tmp_path / "top_level.md"
    f2 = nested_dir / "nested.md"
    
    f1.write_text("...")
    f2.write_text("...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp", "ingest", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env
    )
    
    assert "Resolved 2 URIs" in result.stderr
    assert "Successfully broadcasted 2 items" in result.stderr
