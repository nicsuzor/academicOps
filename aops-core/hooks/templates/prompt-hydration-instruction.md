# Hydrate Before Acting

For work requests (not simple questions), spawn the hydrator first:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Read {temp_path} and provide workflow guidance.")
```

Follow the hydrator's returned execution path (`direct` or `enqueue`) and task specification.
