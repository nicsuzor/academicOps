# Basic Memory MCP Tools Reference

**Source**: https://docs.basicmemory.com/guides/mcp-tools-reference/ (Retrieved 2025-11-18)
**Version**: 0.16.1

## Knowledge Management Tools

### write_note
Creates or updates notes with semantic observations and relations.

**Parameters**:
- `title` (required): Note title
- `content` (required): Note content
- `folder` (required): Target folder path
- `tags` (optional): Tags for categorization
- `project` (optional): Project specification
- `note_type` (optional): Type of note (default: "note")

**Usage**: Create new notes or update existing ones in the knowledge base.

### read_note
Retrieves existing notes with contextual information and related knowledge.

**Parameters**:
- `identifier` (required): Note title or permalink
- `project` (optional): Project name
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Results per page (default: 10)

**Usage**: Read notes with their relations and context.

### edit_note
Incrementally modifies notes using various operations while preserving existing structure.

**Parameters**:
- `identifier` (required): Note title or permalink
- `operation` (required): Edit operation type
  - `append`: Add content to end
  - `prepend`: Add content to beginning
  - `find_replace`: Replace specific text
  - `replace_section`: Replace entire section
- `content` (required): Content to add/replace
- `find_text` (optional): Text to find (for find_replace)
- `section` (optional): Section name (for replace_section)
- `expected_replacements` (optional): Expected number of replacements (default: 1)
- `project` (optional): Project name

**Usage**: Make incremental changes to existing notes without rewriting entire content.

### view_note
Displays notes as formatted artifacts for enhanced readability in Claude Desktop.

**Parameters**:
- `identifier` (required): Note title or permalink
- `project` (optional): Project name
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Results per page (default: 10)

**Usage**: Show notes in a formatted, readable view.

### delete_note
Removes notes from both database and file system, updating search indices and relationships.

**Parameters**:
- `identifier` (required): Note title or permalink
- `project` (optional): Project name

**Usage**: Permanently delete notes (removes file and database entry).

**Important**: This removes the actual file from the filesystem, not just the database entry.

### move_note
Relocates and renames notes while maintaining database consistency and updating search indices.

**Parameters**:
- `identifier` (required): Note title or permalink
- `destination_path` (required): New location/name
- `project` (optional): Project name

**Usage**: Reorganize notes while preserving relationships.

## Search and Discovery Tools

### search_notes
Performs full-text searching across knowledge bases.

**Parameters**:
- `query` (required): Search query string
- `project` (optional): Project name
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Results per page (default: 10)
- `after_date` (optional): Filter by date (YYYY-MM-DD)
- `types` (optional): Filter by entity types (array)
- `entity_types` (optional): Filter by entity types (array)
- `search_type` (optional): Search strategy (default: "text")

**Usage**: Find notes matching search criteria.

### recent_activity
Shows recently modified content with customizable timeframes, types, and depth.

**Parameters**:
- `project` (optional): Project name (omit for cross-project mode)
- `timeframe` (optional): Time window (default: "7d")
  - Natural language: "2 days ago", "last week", "today"
  - Standard format: "7d", "24h", "3 months ago"
- `type` (optional): Filter by content type
- `depth` (optional): Depth of related content (default: 1)

**Usage**: View recent changes across projects or within specific project.

**Cross-project mode**: Omitting the `project` parameter enables discovery across all projects.

### build_context
Loads context from memory:// URLs to navigate knowledge graph relationships and build conversation context.

**Parameters**:
- `url` (required): Memory URL path
  - Format: "folder/note" or "memory://folder/note"
  - Pattern matching: "folder/*" matches all notes in folder
  - Valid characters: letters, numbers, hyphens, underscores, forward slashes
- `project` (optional): Project name
- `timeframe` (optional): Time window (default: "7d")
- `depth` (optional): Relationship depth (default: 1)
- `max_related` (optional): Max related items (default: 10)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 10)

**Usage**: Follow up on previous discussions or explore related topics naturally.

**Memory URL Examples**:
- "specs/search"
- "projects/basic-memory"
- "notes/*"

**Avoid**:
- Double slashes (//)
- Angle brackets (<>)
- Quotes
- Pipes (|)

### list_directory
Browses knowledge base folder structures with optional file pattern filtering and depth configuration.

**Parameters**:
- `dir_name` (optional): Directory path (default: "/")
- `project` (optional): Project name
- `file_name_glob` (optional): File pattern filter
- `depth` (optional): Directory depth (default: 1)

**Usage**: Navigate folder structure and find files.

## Project Management Tools

### list_memory_projects
Displays all available projects with status and statistics.

**Parameters**: None

**Returns**: List of all projects with:
- Project names
- Paths
- Default project indicator

**Usage**: Administrative tool for viewing configured projects. For academicOps, ALWAYS use `project="main"` instead of calling this tool.

### create_memory_project
Initializes new knowledge bases with specified names, paths, and optional default project designation.

**Parameters**:
- `project_name` (required): Name for new project (must be unique)
- `project_path` (required): File system path for project storage
- `set_default` (optional): Whether to set as default project (default: false)

**Returns**: Confirmation message with project details

**Usage**: Create new Basic Memory projects programmatically.

**Notes**:
- Project directory will be created if it doesn't exist
- Project name must be unique across all projects

### delete_project
Removes project configuration references without deleting actual files.

**Parameters**:
- `project_name` (required): Name of project to delete

**Returns**: Confirmation message

**Usage**: Remove project from configuration and database.

**Important**: This does NOT delete actual files on disk—only removes the project from Basic Memory's configuration and database records.

### sync_status
Checks file synchronization progress across all projects without requiring parameters.

**Parameters**: None

**Returns**:
- Sync progress information
- Background operation status
- Sync issues or conflicts

**Usage**: Monitor synchronization health and identify problems.

## Utility Tools

### read_content
Accesses raw file content supporting text, images, and binary formats with direct file system access.

**Parameters**:
- `path` (required): File path or permalink
- `project` (optional): Project name

**Returns**: Raw file content

**Supported formats**:
- Text files
- Images
- Binary files

**Usage**: Access file content without knowledge graph processing.

### canvas
Generates Obsidian canvas visualizations from specified nodes and edges.

**Parameters**:
- `nodes` (required): Array of node objects
- `edges` (required): Array of edge objects
- `title` (required): Canvas title
- `folder` (required): Destination folder
- `project` (optional): Project name

**Returns**: Created canvas file

**Usage**: Create visual knowledge graph representations.

## Project Modes

Basic Memory supports three operational modes:

### Multi-Project Mode (Default)
- Assistants specify project explicitly in each tool call
- **For academicOps**: ALWAYS use `project="main"` parameter
- Enables cross-project workflows (when needed)

### Default Project Mode
- Automatically uses configured default project unless overridden
- Set via `basic-memory project default <project_name>`
- Reduces need for explicit project parameters
- Can still override with explicit project parameter

### Single Project Mode
- Locks entire sessions to one project via CLI flags
- Configured at MCP server startup
- No project discovery or switching
- Most restrictive but simplest for single-project workflows

## Best Practices

### Project Selection
**For academicOps framework**: ALWAYS use `project="main"` in ALL bmem MCP tool calls. This is mandatory and non-negotiable.

### Search Strategy
- Use `search_notes` for keyword searches
- Use `build_context` for following knowledge graph relationships
- Use `recent_activity` for temporal discovery
- Combine filters (date, type, entity_types) for precision

### File Management
- Use `delete_note` to remove both file and database entry
- Use `move_note` to reorganize while preserving relations
- Use `edit_note` for incremental changes (more efficient than rewriting)
- Use `read_content` for raw file access without graph processing

### Sync Management
- Check `sync_status` regularly for health monitoring
- Real-time sync is automatic (no manual intervention needed)
- Database reset (`basic-memory reset`) is nuclear option for stale entries
