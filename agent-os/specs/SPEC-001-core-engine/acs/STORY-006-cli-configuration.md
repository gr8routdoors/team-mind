# STORY-006: CLI Configuration & Environment Variables

## Acceptance Criteria

### AC-001: Global Database Path Configuration
- Given an available MCP server entry point
- When the user provides a `--db-path` argument globally (e.g. `team-mind-mcp --db-path /custom/path.db start`)
- Then the server uses that exact path to initialize the `StorageAdapter`

### AC-002: Environment Variable Fallback
- Given the user has set the `TEAM_MIND_DB_PATH` environment variable
- When the server starts without a `--db-path` explicit argument
- Then the storage layer resolves to the environment variable's path

### AC-003: Default Fallback Path
- Given no database path arguments or environment variables are provided
- When the server starts
- Then the default path is resolved correctly as `~/.team-mind/database.sqlite`
- And the `.team-mind` parent directory is automatically created if it doesn't already exist
