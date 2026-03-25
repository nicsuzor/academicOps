with open("polecat/cli.py") as f:
    content = f.read()

# Replace the nuke function logic
old_nuke = '''def nuke(ctx, target, force):
    """Destroy a polecat (remove worktree and branch)."""
    # Validate task ID before any operations
    try:
        validate_task_id_or_raise(task_id)
    except TaskIDValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    manager = PolecatManager(home_dir=ctx.obj.get("home"))
    try:
        manager.nuke_worktree(task_id, force=force)
        print(f"Nuked polecat {task_id}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)'''

new_nuke = '''def nuke(ctx, target, force):
    """Destroy a polecat or crew worker, or clean up stale branches when run without args."""
    manager = PolecatManager(home_dir=ctx.obj.get("home"))

    if target:
        crew_path = manager.crew_dir / target
        if crew_path.exists():
            try:
                manager.nuke_crew(target, force=force)
                return
            except (ValueError, RuntimeError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        # Fallback to worktree logic
        try:
            validate_task_id_or_raise(target)
            manager.nuke_worktree(target, force=force)
            print(f"Nuked polecat {target}")
            return
        except TaskIDValidationError:
            print(f"Error: Target '{target}' is not a valid crew worker or task ID.", file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Target not provided, run stale cleanup
    print("No target provided. Cleaning up stale branches...")'''

# Find the end of nuke function (before list command)
start_idx = content.find("def nuke(ctx, target, force):")
end_idx = content.find('@main.command("list")')

content = content[:start_idx] + new_nuke + "\n\n\n" + content[end_idx:]

with open("polecat/cli.py", "w") as f:
    f.write(content)
