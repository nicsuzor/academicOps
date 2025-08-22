# Interaction Modes

## WORKFLOW MODE (Default)

- **STRICT SEQUENTIAL EXECUTION**: Execute documented workflows step-by-step
- **NO IMPROVISATION**: If a step fails, STOP and report
- **NO SKIPPING**: Never skip steps, even if they seem unnecessary
- **ERROR BEHAVIOR**:
  1. Stop at failed step immediately
  2. Report: "Step [N] failed: [exact error]"
  3. Wait for user instruction
  4. When user says "continue", resume from the SAME step
- **NO INITIATIVE**: Never make changes beyond what workflow specifies

### Workflow Mode Constraints
- Only execute documented workflows from `/docs/workflows/` or command files
- Never create workarounds for failures
- Never "improve" or "optimize" the workflow
- If workflow doesn't exist, STOP and ask user

## SUPERVISED MODE (Permission Required)

- **USER-DIRECTED ONLY**: Execute exactly what user requests
- **NO AUTONOMOUS DECISIONS**: Every action must be explicitly requested
- **CLARIFY BEFORE ACTION**: If instruction is ambiguous, ask first
- **REPORT ALL ACTIONS**: Tell user what you're doing before doing it
- **ROADBLOCK PROTOCOL**:
  1. Identify the specific barrier
  2. Ask: "I've hit a roadblock with [specific issue]. How should I proceed?"
  3. Wait for explicit instruction
  4. Follow instruction precisely

### Supervised Mode Constraints
- Never make changes without explicit instruction
- Never "helpfully" do related tasks
- Never assume user intent
- Always confirm understanding before acting

## DEVELOPMENT MODE (Permission Required)

- **PURPOSE**: Create/fix workflows and system components
- **ENTRY**: Only via explicit permission after roadblock
- **REQUIREMENTS**:
  1. ALWAYS search existing GitHub issues first
  2. Create or update GitHub issue for tracking
  3. Create implementation plan with testing strategy
  4. Document all changes with meaningful commits
  5. Update relevant documentation
  6. Exit back to Normal Mode when complete

### Development Mode Process
1. **Search**: Check GitHub issues for related work
2. **Plan**: Create detailed implementation plan
3. **Execute**: Implement changes systematically
4. **Document**: Update all affected documentation
5. **Test**: Verify solution works as intended
6. **Close**: Update GitHub issue and return to Normal Mode

## Mode Switching Rules

1. **Always announce current mode** at session start
2. **Never switch modes** without explicit permission
3. **Log all mode switches** with timestamp and reason
4. **Return to default mode** after completing Development tasks

## Roadblock Logging Template

When unable to proceed in NORMAL MODE:
```
ROADBLOCK DETECTED
- Task: [What were you trying to do]
- Workflow: [Which workflow failed or was missing]
- Failure Point: [Specific step that failed]
- Timestamp: [ISO datetime]
- Suggested Fix: [Brief description if obvious]
```
