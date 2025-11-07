# Hydra Configuration - Complete Guide

**Last Updated:** 2025-10-30 **Hydra Version:** 1.3+ (backward compatible with 1.1+)

Complete reference for Hydra configuration in academicOps projects. Covers principles, patterns, testing, and solutions to common errors.

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Quick Start](#quick-start)
3. [Directory Structure](#directory-structure)
4. [Composition & Defaults List](#composition--defaults-list)
5. [Testing with Hydra](#testing-with-hydra)
6. [Interpolation Patterns](#interpolation-patterns)
7. [Secrets & Environment Variables](#secrets--environment-variables)
8. [Common Errors & Solutions](#common-errors--solutions)
9. [Debugging Tools](#debugging-tools)
10. [Best Practices](#best-practices)

---

## Core Principles

### The academicOps Way

- **NO configuration in code** - All config lives in YAML files
- **NO direct environment variable access** - Use `${oc.env:VAR}` in YAML only
- **NO defaults** - Fail fast when config is missing (see Axiom 7)
- **Composable, not monolithic** - Small, focused YAML files that compose
- **Explicit, not implicit** - Always use `_self_`, never rely on defaults

### Key Hydra Concept

**"Last one wins"** - If multiple configs define the same value, the last one in composition order wins.

---

## Quick Start

### Minimal Application

```python
# main.py
import hydra
from omegaconf import DictConfig


@hydra.main(version_base=None, config_path="conf", config_name="config")
def run(cfg: DictConfig):
    print(cfg.db.host, cfg.app.workers)


if __name__ == "__main__":
    run()
```

```yaml
# conf/config.yaml
defaults:
  - _self_
  - db: postgres
  - app: api

seed: 42
```

```yaml
# conf/db/postgres.yaml
driver: postgres
host: localhost
port: 5432
```

```yaml
# conf/app/api.yaml
workers: 4
log_level: INFO
```

**Run with overrides:**

```bash
python main.py db.host=prod-db.example.com app.workers=8
python main.py db=sqlite  # Switch to conf/db/sqlite.yaml
```

---

## Directory Structure

### Recommended Layout

```
conf/
├── config.yaml           # Primary config with defaults list
├── db/                   # Config group: database options
│   ├── postgres.yaml
│   ├── sqlite.yaml
│   └── mysql.yaml
├── app/                  # Config group: application variants
│   ├── api.yaml
│   └── worker.yaml
├── env/                  # Config group: environments
│   ├── local.yaml
│   ├── staging.yaml
│   └── prod.yaml
└── cache/                # Config group: cache backends
    ├── redis.yaml
    └── memory.yaml
```

### Naming Conventions

- **Groups = Nouns** (db, cache, env, dataset) not verbs
- **Options = Descriptive** (postgres, redis, prod)
- **One responsibility per file** - avoid mega-configs

---

## Composition & Defaults List

### Defaults List Syntax

The `defaults` list controls composition order. **It is NOT included in the final config.**

```yaml
defaults:
  - _self_ # Position of this config's values
  - db: postgres # Select from db/ group
  - optional cache: redis # Don't error if missing
  - override db: sqlite # Replace previous db choice
  - db@replica: postgres # Second instance with custom package
```

### The `_self_` Keyword (Critical!)

Controls where the primary config's values appear in composition order.

```yaml
# Pattern 1: Primary config OVERRIDES defaults (RECOMMENDED)
defaults:
  - db: postgres
  - _self_ # ← config.yaml values placed AFTER db/postgres.yaml

db:
  port: 3306 # This WINS over postgres.yaml's port
```

```yaml
# Pattern 2: Defaults OVERRIDE primary config (rare)
defaults:
  - _self_ # ← config.yaml values placed FIRST
  - db: postgres

db:
  port: 3306 # db/postgres.yaml WINS over this
```

**Rule:** Always include `_self_` explicitly. Hydra 1.1+ warns if missing.

### Composition Order Example

```yaml
# conf/config.yaml
defaults:
  - db: postgres
  - cache: redis
  - _self_

app_name: myapp
db:
  port: 9999 # Override postgres default
```

**Composition order:**

1. `db/postgres.yaml` → `{driver: postgres, host: localhost, port: 5432}`
2. `cache/redis.yaml` → adds `{cache: {host: localhost, port: 6379}}`
3. `_self_` (config.yaml) → overrides `db.port: 9999`, adds `app_name: myapp`

**Final config:**

```yaml
db:
  driver: postgres
  host: localhost
  port: 9999 # ← Overridden by config.yaml
cache:
  host: localhost
  port: 6379
app_name: myapp
```

### The `override` Keyword

Use `override` to **change** a group selection that was already defined (e.g., in a parent config).

**Problem:**

```yaml
# base.yaml
defaults:
  - db: postgres

# child.yaml
defaults:
  - base
  - db: sqlite # ❌ ERROR: "db appears more than once"
```

**Solution:**

```yaml
# child.yaml
defaults:
  - base
  - override db: sqlite # ✅ Replace inherited db choice
```

**When to use:**

- Inheriting from a base config that already selects a group
- Changing a group choice later in the same defaults list

**When NOT to use:**

- First time selecting a group (just use `db: postgres`)

### Package Directive (`@package`)

Control where a config file's content is placed in the output tree.

```yaml
# conf/db/postgres.yaml (default behavior)
# Content placed at: db.driver, db.host, db.port
driver: postgres
host: localhost
port: 5432
```

```yaml
# conf/db/postgres.yaml
# @package _global_
# Content placed at ROOT: driver, host, port
driver: postgres
host: localhost
port: 5432
```

**Using packages in defaults:**

```yaml
# config.yaml
defaults:
  - db@primary: postgres # Package as 'primary'
  - db@replica: postgres # Package as 'replica'

# Result:
# primary:
#   driver: postgres
#   host: localhost
#   port: 5432
# replica:
#   driver: postgres
#   host: localhost
#   port: 5433
```

---

## Testing with Hydra

### Test Setup Pattern

```python
# conftest.py
import pytest
from hydra import initialize_config_dir, compose
from pathlib import Path


@pytest.fixture
def hydra_cfg():
    """Initialize Hydra for testing."""
    config_dir = Path(__file__).parent / "conf"
    with initialize_config_dir(
        version_base=None, config_dir=str(config_dir.absolute())
    ):
        cfg = compose(config_name="config")
        yield cfg
```

### Testing with Overrides

```python
def test_db_override(tmp_path):
    """Test switching database backend."""
    config_dir = Path(__file__).parent / "conf"

    with initialize_config_dir(
        version_base=None, config_dir=str(config_dir.absolute())
    ):
        cfg = compose(
            config_name="config", overrides=["db=sqlite", "db.path=/tmp/test.db"]
        )

        assert cfg.db.driver == "sqlite"
        assert cfg.db.path == "/tmp/test.db"
```

### Common Test Pattern: Multiple Configs

```python
@pytest.mark.parametrize("env", ["local", "staging", "prod"])
def test_env_configs(env):
    """Verify each environment config loads."""
    config_dir = Path(__file__).parent / "conf"

    with initialize_config_dir(
        version_base=None, config_dir=str(config_dir.absolute())
    ):
        cfg = compose(config_name="config", overrides=[f"env={env}"])

        # Verify environment-specific settings
        if env == "prod":
            assert cfg.app.log_level == "INFO"
            assert not cfg.debug
        elif env == "local":
            assert cfg.app.log_level == "DEBUG"
            assert cfg.debug
```

### Testing Interpolations Resolve

```python
from omegaconf import OmegaConf


def test_interpolations_resolve(hydra_cfg):
    """Ensure all interpolations resolve without errors."""
    # Force resolution
    resolved = OmegaConf.to_container(hydra_cfg, resolve=True)

    # Verify critical paths
    assert "region" in resolved["env"]
    assert resolved["env"]["region"] in resolved["bucket"]
```

### Golden Config Tests

```python
def test_prod_config_matches_golden():
    """Prevent accidental prod config changes."""
    config_dir = Path(__file__).parent / "conf"

    with initialize_config_dir(
        version_base=None, config_dir=str(config_dir.absolute())
    ):
        cfg = compose(config_name="config", overrides=["env=prod"])
        resolved = OmegaConf.to_container(cfg, resolve=True)

        # Check critical production values
        assert resolved["db"]["host"] == "prod-db.internal.ap-south-1"
        assert resolved["app"]["workers"] == 16
        assert not resolved["debug"]
```

---

## Interpolation Patterns

### Basic Interpolation

Keep values DRY by referencing other config values.

```yaml
# conf/env/prod.yaml
region: ap-south-1
bucket: myapp-${env.region} # → myapp-ap-south-1
db:
  host: prod-db.internal.${env.region} # → prod-db.internal.ap-south-1
```

### Environment Variable Interpolation

```yaml
# conf/db/postgres.yaml
user: ${oc.env:DB_USER} # Required - fails if missing
password: ${oc.env:DB_PASSWORD} # Required - fails if missing
host: ${oc.env:DB_HOST,localhost} # Optional - defaults to localhost
```

**Key syntax:**

- `${oc.env:VAR}` - Required env var (fails if missing)
- `${oc.env:VAR,default}` - Optional with default
- `${oc.env:VAR,?}` - Required (alternative syntax)

### Conditional Config Selection

```yaml
# conf/config.yaml
defaults:
  - db: ${oc.env:DB_TYPE,postgres} # Use env var, default to postgres
  - optional monitoring: ${oc.env:ENABLE_MONITORING,null}
```

### Cross-Reference Interpolation

```yaml
# conf/config.yaml
db:
  host: localhost
  port: 5432

app:
  db_url: postgres://${db.host}:${db.port}/mydb
  # → postgres://localhost:5432/mydb
```

### Resolver Functions

OmegaConf provides built-in resolvers:

```yaml
# Get environment variable
path: ${oc.env:HOME}/data

# Decode base64
secret: ${oc.decode:base64,SGVsbG8=}

# Conditional (ternary)
log_level: ${oc.select:debug,DEBUG,INFO}
```

---

## Secrets & Environment Variables

### The academicOps Way

**Principle:** NO secrets in source code. NO fallback defaults for secrets.

```yaml
# ✅ CORRECT - Fail fast if secret missing
# conf/db/postgres.yaml
user: ${oc.env:DB_USER,?} # '?' means required
password: ${oc.env:DB_PASSWORD,?}
```

```yaml
# ❌ WRONG - Silent fallback masks missing config
user: ${oc.env:DB_USER,admin}
password: ${oc.env:DB_PASSWORD,default123}
```

### Logging Safely

```python
import logging
from omegaconf import OmegaConf

log = logging.getLogger(__name__)


@hydra.main(...)
def run(cfg: DictConfig):
    # ✅ SAFE - Log non-sensitive config
    log.info(
        "Connecting to database",
        extra={"db_host": cfg.db.host, "db_user": cfg.db.user, "db_port": cfg.db.port},
    )

    # ❌ NEVER log passwords/secrets
    # log.info(f"Password: {cfg.db.password}")  # PROHIBITED
```

### Structured Config with Secrets

```python
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore


@dataclass
class DBConfig:
    driver: str
    host: str
    port: int
    user: str
    password: str  # No default - must be provided


cs = ConfigStore.instance()
cs.store(name="db_schema", node=DBConfig)
```

```yaml
# conf/db/postgres.yaml
# @package _global_.db
driver: postgres
host: localhost
port: 5432
user: ${oc.env:DB_USER,?}
password: ${oc.env:DB_PASSWORD,?}
```

---

## Common Errors & Solutions

### Error 1: "X appears more than once in the final defaults list"

**Cause:** Same config group selected multiple times without `override`.

```yaml
# ❌ WRONG
defaults:
  - db: postgres
  - db: sqlite # Error!
```

**Solution:** Use `override` for the second selection:

```yaml
# ✅ CORRECT
defaults:
  - db: postgres
  - override db: sqlite # Replaces postgres
```

### Error 2: "Multiple values for X. To override use 'override X: value'"

**Cause:** Inherited config already selected a group.

```yaml
# base.yaml
defaults:
  - db: postgres

# child.yaml
defaults:
  - base
  - db: sqlite # ❌ Conflicts with inherited db: postgres
```

**Solution:**

```yaml
# child.yaml
defaults:
  - base
  - override db: sqlite # ✅ Replace inherited choice
```

### Error 3: Missing `_self_` Warning

**Warning message:**

```
'config' is validated against ConfigStore schema.
This behavior is deprecated in Hydra 1.1 and will be removed in Hydra 1.2.
```

**Cause:** Primary config has values but defaults list missing `_self_`.

**Solution:** Add `_self_` explicitly:

```yaml
# ✅ CORRECT
defaults:
  - db: postgres
  - _self_ # Always include!

my_value: 123
```

### Error 4: Interpolation Not Resolving

**Symptom:** `${db.host}` appears literally in output.

**Cause:** Using `OmegaConf.to_container()` without `resolve=True`.

**Solution:**

```python
# ❌ WRONG
plain_dict = OmegaConf.to_container(cfg)

# ✅ CORRECT
plain_dict = OmegaConf.to_container(cfg, resolve=True)
```

### Error 5: "Could not override 'X'. No match in config."

**Cause:** Trying to override a key that doesn't exist.

**Solution:** Use `+` prefix to add new keys:

```bash
# ❌ WRONG (if 'new_key' doesn't exist)
python main.py new_key=value

# ✅ CORRECT
python main.py +new_key=value
```

---

## Debugging Tools

### Command-Line Inspection

```bash
# Show defaults tree structure
python main.py --info defaults-tree

# Show final composition list
python main.py --info defaults

# Show resulting configuration
python main.py --cfg job

# Show all config sources
python main.py --info all

# Validate config without running
python main.py --cfg job > /dev/null
```

### Example: `--info defaults-tree`

```
Config search path:
  provider=hydra, path=pkg://hydra.conf
  provider=main, path=/app/conf

Defaults Tree
*config
├─ db: postgres
├─ cache: redis
└─ env: local
```

### Example: `--cfg job`

```yaml
db:
  driver: postgres
  host: localhost
  port: 5432
cache:
  host: localhost
  port: 6379
env:
  region: local
  debug: true
```

### Programmatic Debugging

```python
from omegaconf import OmegaConf


@hydra.main(...)
def run(cfg: DictConfig):
    # Print full config as YAML
    print(OmegaConf.to_yaml(cfg))

    # Print specific subtree
    print(OmegaConf.to_yaml(cfg.db))

    # Check if key exists
    if OmegaConf.select(cfg, "optional.path") is None:
        print("optional.path not set")
```

---

## Best Practices

### 1. Always Use `_self_` Explicitly

```yaml
# ✅ GOOD
defaults:
  - db: postgres
  - _self_

# ❌ BAD (implicit behavior)
defaults:
  - db: postgres
```

### 2. Name Groups After Nouns, Not Verbs

```yaml
# ✅ GOOD
defaults:
  - db: postgres
  - cache: redis
  - env: prod

# ❌ BAD
defaults:
  - use_postgres: true
  - enable_redis: true
```

### 3. Prefer Config Groups Over Booleans

```yaml
# ✅ GOOD - Explicit config files
defaults:
  - cache: redis # conf/cache/redis.yaml
  - cache: memory # conf/cache/memory.yaml

# ❌ BAD - Boolean flags
use_redis: true
cache_ttl: 3600
cache_host: localhost
```

### 4. Fail Fast - No Silent Defaults

```yaml
# ✅ GOOD - Required value fails if missing
password: ${oc.env:DB_PASSWORD,?}

# ❌ BAD - Silent fallback masks problems
password: ${oc.env:DB_PASSWORD,default123}
```

### 5. Keep Configs Small and Focused

```yaml
# ✅ GOOD - One responsibility per file
# conf/db/postgres.yaml (5 lines)
driver: postgres
host: localhost
port: 5432

# ❌ BAD - Mega config file
# conf/everything.yaml (500 lines)
```

### 6. Test Configs Like Code

- Use pytest fixtures for Hydra initialization
- Test each environment config loads
- Verify interpolations resolve
- Create golden tests for production configs

### 7. Resolve at the Edge, Not the Core

```python
# ✅ GOOD - Keep DictConfig in core logic
def process_data(cfg: DictConfig):
    db_host = cfg.db.host  # Interpolations still work
    # ... business logic ...


# Only resolve when crossing boundaries
def send_to_external_api(cfg: DictConfig):
    payload = OmegaConf.to_container(cfg.api, resolve=True)
    requests.post(url, json=payload)
```

### 8. Document Composition Order

```yaml
# conf/config.yaml
defaults:
  # Base infrastructure
  - db: postgres
  - cache: redis

  # Application variant
  - app: api

  # Environment overlay (overrides above)
  - env: local

  # This config's values override everything
  - _self_

# Override order: db → cache → app → env → config.yaml
```

### 9. Use Multi-Run for Experiments

```bash
# Test all combinations
python main.py -m db=postgres,sqlite cache=redis,memory env=local,prod

# Each run gets isolated output directory
# outputs/2025-10-30/14-23-01/
```

### 10. Version Control `.hydra/` Output

Add to `.gitignore`:

```
# Hydra output
outputs/
multirun/
.hydra/
```

But keep `conf/` in version control.

---

## Quick Reference Card

### Defaults List Syntax

```yaml
defaults:
  - CONFIG # Include config file
  - GROUP: value # Select from group
  - optional GROUP: val # Suppress error if missing
  - override GROUP: val # Replace previous selection
  - GROUP@pkg: val # Custom package location
  - _self_ # Position of this config
```

### Interpolation Syntax

```yaml
${other.key}                    # Reference config value
${oc.env:VAR}                   # Required env var
${oc.env:VAR,default}           # Optional env var with default
${oc.env:VAR,?}                 # Required env var (alt syntax)
${oc.select:path,default}       # Select with fallback
```

### Command-Line Overrides

```bash
python main.py key=value              # Override value
python main.py group=option           # Switch group selection
python main.py +new_key=value         # Add new key
python main.py ~group                 # Remove group from defaults
python main.py group@pkg=option       # Override with package
python main.py -m key=v1,v2,v3        # Multi-run sweep
```

### Common Keywords

| Keyword    | Purpose                                |
| ---------- | -------------------------------------- |
| `_self_`   | Position primary config in composition |
| `_global_` | Place content at root                  |
| `_group_`  | Use group path as package              |
| `override` | Replace existing group selection       |
| `optional` | Don't error if config missing          |

---

## Practical Patterns

### Pattern: Environment Overlays

```yaml
# conf/config.yaml
defaults:
  - db: postgres
  - app: api
  - env: local # Default environment
  - _self_

# Switch at runtime
# python main.py env=prod
```

```yaml
# conf/env/local.yaml
debug: true
app:
  log_level: DEBUG

# conf/env/prod.yaml
debug: false
app:
  log_level: INFO
```

### Pattern: Multiple Instances

```yaml
# conf/config.yaml
defaults:
  - db@primary: postgres
  - db@replica: postgres
  - _self_

# Override replica port
replica:
  port: 5433
```

**Result:**

```yaml
primary:
  driver: postgres
  host: localhost
  port: 5432
replica:
  driver: postgres
  host: localhost
  port: 5433
```

### Pattern: Feature Flags

```yaml
# conf/config.yaml
defaults:
  - optional features/monitoring: ${oc.env:ENABLE_MONITORING,null}
  - optional features/caching: ${oc.env:ENABLE_CACHE,null}
```

### Pattern: Validated Schemas

```python
# schema.py
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore


@dataclass
class DBConfig:
    driver: str
    host: str
    port: int
    # No defaults - all required!


@dataclass
class Config:
    db: DBConfig
    app_name: str


cs = ConfigStore.instance()
cs.store(name="base_schema", node=Config)
```

```python
# main.py
@hydra.main(version_base=None, config_name="base_schema")
def run(cfg: Config):  # Type-checked!
    print(cfg.db.host)
```

**Benefits:**

- Type checking in IDE
- Automatic validation
- Fails fast on typos (`cfg.db.hozt` → error)

---

## References

- [Official Hydra Documentation](https://hydra.cc/)
- [Defaults List Guide](https://hydra.cc/docs/advanced/defaults_list/)
- [Composition Order Changes](https://hydra.cc/docs/upgrades/1.0_to_1.1/default_composition_order/)
- [OmegaConf Resolvers](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html)

---

**End of Guide**
