# Technology Stack & Architecture

## Core Technologies

### Language & Runtime
- **Python 3.10+**
  - Modern async/await support
  - Type hints throughout
  - Rich ecosystem for data science

### Package Management
- **uv**: Fast, reliable Python package manager
  - Always use: `uv run python ...`
  - Dev dependencies: `uv add --dev <package>`
  - Lock file ensures reproducibility

### Key Dependencies

#### Data Validation & Configuration
- **Pydantic v2**: Data validation and settings
  - Strict type checking
  - Automatic validation
  - JSON schema generation

- **Hydra-core + OmegaConf**: Configuration management
  - Hierarchical configuration composition
  - Command-line overrides
  - Interpolation support

#### Async & Concurrency
- **anyio**: Core async support
  - All I/O operations async
  - Concurrent agent execution

- **autogen-core**: Agent communication runtime (if used)
  - Message routing via topics
  - Agent lifecycle management

#### Web & API
- **FastAPI**: REST API framework
  - Auto-generated OpenAPI docs
  - WebSocket support
  - Async request handling

- **httpx**: Async HTTP client

#### Testing
- **pytest + pytest-asyncio**: Testing framework
  - Async test support
  - Fixtures for common setups
  - Parallel test execution

## Architecture Patterns

### Agent-Based Architecture

#### Core Components
1. **Agent**: Base class for all processing units.
2. **Orchestrator**: Manages flow execution and routes messages.
3. **Contract**: Pydantic models for messages, ensuring type-safe communication.

### Configuration Architecture

- Behavior is defined in YAML files.
- Hierarchical composition allows for building complex configurations from smaller files.
- Interpolation allows for referencing other configuration values.
- Overrides can be provided via the command line.

### Data Flow Architecture

1. **YAML** is loaded by **Hydra** into an **OmegaConf** object.
2. The **OmegaConf** object is validated by **Pydantic**.
3. Data flows between agents via Pydantic models (e.g., `AgentInput` -> `Agent` -> `AgentOutput`).

### Storage Architecture

- A factory pattern is often used for creating storage backends.
- Storage types can include local files, BigQuery, GCS, etc.

### Architecture Principles

#### Async-First
- Better resource utilization.
- Responsive user experience.
- Natural fit for I/O-heavy workloads.

#### Modularity
- Small, focused components.
- Clear interfaces.
- Composition over inheritance.

#### Type Safety
- Pydantic models everywhere.
- Type hints required.
- Runtime validation.

#### Configuration-Driven
- Behavior defined in YAML.
- No hardcoded values.
- Environment-specific overrides.

#### Error Handling
- Fail fast with clear messages.
- Validation at boundaries.
- No defensive programming.
- Trust data contracts.