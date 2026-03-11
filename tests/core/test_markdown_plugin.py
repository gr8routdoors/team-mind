"""
STORY-004: Markdown Vector Plugin
"""
import pytest

def test_markdown_semantic_ingestion():
    """
    AC-001: Markdown Semantic Ingestion
    """
    # Given the MarkdownPlugin is active
    
    # When it receives a .process_bundle() event containing a .md resource
    
    # Then it chunks the text and requests embeddings for each chunk
    # And it stores the embeddings along with the Source Pointer (URI) in the StorageAdapter
    pass

def test_markdown_tool_registration():
    """
    AC-002: Tool Registration
    """
    # Given the MCPGateway and PluginRegistry are online
    
    # When the MarkdownPlugin initializes
    
    # Then it successfully registers the semantic_search tool
    # And it is visible to MCP clients
    pass

def test_markdown_skips_non_markdown_resources():
    """
    AC-003: Skips Non-Markdown Resources
    """
    # Given a bundle containing image.png and notes.md
    
    # When the MarkdownPlugin processes the bundle
    
    # Then it successfully parses notes.md
    # And it silently ignores image.png without throwing an error
    pass
