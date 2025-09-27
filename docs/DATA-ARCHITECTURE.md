# Data Architecture & Schema Contracts

## Core Principles

### Schema-Data Contract
When modifying data structures, ALL system components must be updated atomically:
- Class definitions (Pydantic models)
- Database schemas (BigQuery tables, etc.)
- SQL queries referencing fields
- Serialization/deserialization logic
- Test fixtures and sample data
- API contracts and documentation

**Example**: Moving `uri` from Record to `metadata` requires updating:
1. Record class definition
2. BigQuery table schema
3. All SQL SELECT statements
4. Data loading/saving logic
5. Test data structures

### No Defensive Programming
The project philosophy explicitly rejects defensive coding:
- **Trust the schema**: Data should match defined schemas
- **Let errors propagate**: Academic users need visibility
- **No silent failures**: Remove try/except blocks that hide problems
- **No fallback values**: Avoid "safe" defaults that mask issues
- **Fail fast**: Better to error immediately than produce incorrect results

```python
# BAD: Defensive programming
def get_uri(record):
    try:
        return record.metadata.get('uri', record.uri if hasattr(record, 'uri') else None)
    except:
        return None

# GOOD: Trust the schema
def get_uri(record):
    return record.metadata['uri']  # Let KeyError propagate if missing
```

### Configuration vs Errors
- **User configuration**: Validate early, fail with clear messages
- **Data processing**: Trust inputs match schema
- **External data**: Validate at ingestion boundaries only
- **Internal data**: Assume correctness, let errors surface

## Data Models

### Record Structure
The Record class represents a unit of data for processing:
- Core fields defined in Pydantic model
- `metadata` dict contains flexible fields like `uri`
- All fields must be explicitly defined in schema
- No dynamic field addition during processing

### Column Mapping
User-supplied column mappings add query complexity:
- Build SQL dynamically based on mappings
- Use `SELECT *` as temporary solution when needed
- Document mapping requirements clearly
- Validate mappings at configuration time

### Storage Contracts
Each storage backend must respect data contracts:
- BigQuery: Schema must match Pydantic models exactly
- Local storage: JSON serialization preserves all fields
- Vector DBs: Embedding generation respects schema
- No storage-specific field transformations

## Testing Philosophy

### Test Data Integrity
- Test fixtures must match current schemas
- Remove obsolete fields from test data
- Update tests when schemas change
- No "legacy" test structures

### Schema Evolution
When schemas change:
1. Update all test fixtures
2. Migrate existing data
3. Version schemas if needed
4. Document breaking changes

## Best Practices

### Making Schema Changes
1. **Plan the change**: Identify all affected components
2. **Update atomically**: Change all components together
3. **Test thoroughly**: Ensure data flows correctly
4. **Document changes**: Update this file and changelogs
5. **Communicate**: Alert team to breaking changes

### Data Validation
- Validate at system boundaries (API inputs, file loads)
- Use Pydantic's validation for all data models
- Don't re-validate internally
- Trust validated data throughout pipeline

### Error Messages
When data errors occur:
- Provide clear context (which field, what value)
- Include schema expectations
- Suggest fixes if possible
- Never suppress or genericize errors

## Common Pitfalls

### Avoid These Anti-Patterns
1. **Dual field support**: Don't check multiple locations for same data
2. **Silent migrations**: Don't auto-convert between schemas
3. **Defensive defaults**: Don't provide fallback values
4. **Schema guessing**: Don't infer structure from data
5. **Partial updates**: Don't update schema in only some components

### Remember
- Data contracts are promises between components
- Breaking contracts breaks trust
- Explicit schemas enable confident development
- Errors are better than incorrect results