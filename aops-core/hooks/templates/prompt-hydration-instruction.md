# Hydrate Before Acting

**Execute this Task call:**
```
Task(subagent_type="aops-core:prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Read {temp_path} and provide workflow guidance.")
```

Then follow the returned execution path.
