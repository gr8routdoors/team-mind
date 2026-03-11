"""
STORY-000: Executable Packaging & Delivery
"""
import pytest
import subprocess
import os

def test_packaging_valid_package_build():
    """
    AC-001: Valid Package Build
    """
    # Given a properly structured pyproject.toml
    assert os.path.exists("pyproject.toml")
    
    # When the user executes uv build
    result = subprocess.run(["uv", "build"], capture_output=True, text=True)
    
    # Then the project successfully compiles into a .whl and .tar.gz distribution
    assert result.returncode == 0, f"uv build failed: {result.stderr}"
    assert os.path.exists("dist"), "dist directory not found"
    
    # Check that wheel and tar.gz were created
    files = os.listdir("dist")
    assert any(f.endswith(".whl") for f in files), "No wheel file found in dist/"
    assert any(f.endswith(".tar.gz") for f in files), "No tar.gz file found in dist/"

def test_packaging_cli_entry_point_execution():
    """
    AC-002: CLI Entry Point Execution
    """
    # Given the package is correctly installed (we simulate execution via uv run)
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    
    # When a user invokes the CLI entry point
    result = subprocess.run(
        ["uv", "run", "team-mind-mcp"], 
        capture_output=True, 
        text=True,
        env=env
    )
    
    # Then the application triggers the main MCP server startup routine
    # And returns a successful exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Team Mind MCP Server initializing..." in result.stdout
