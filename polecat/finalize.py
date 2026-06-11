#!/usr/bin/env python3
"""Polecat finalize command.

Hosts the ``polecat finish`` Click command, extracted from cli.py as part
of the Polecat v2 module split. Body is intentionally a near-verbatim move
— behaviour is unchanged.
"""

import os
import sys
from pathlib import Path

# Add aops-core to path for lib imports (mirrors polecat/cli.py).
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import click

from polecat.manager import PolecatManager


@click.command(name="finish")
@click.option("--no-push", is_flag=True, help="Skip pushing to remote")
@click.option("--nuke", "do_nuke", is_flag=True, help="Also remove the worktree after finishing")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompts (required in non-interactive mode)",
)
@click.option(
    "--force-done",
    is_flag=True,
    help="Force task status to 'done' even if no git changes detected",
)
@click.option("--project", "-p", default=None, help="Override task project (used by auto-finish)")
@click.option(
    "--partial",
    "is_partial",
    is_flag=True,
    help=(
        "Honest partial stop: the chunk was too big for one session. Files the PR as a "
        "DRAFT and releases the task as 'partial' (not 'merge_ready'). See the "
        "partial-work doctrine — ship the finished part, declare the rest deferred."
    ),
)
@click.option("--branch", "-b", default=None, help="Override/specify the custom/shared branch name")
@click.pass_context
def finish_cmd(ctx, no_push, do_nuke, force, force_done, project, is_partial, branch):
    """Mark current task as ready for merge — or as a partial (draft) stop.

    Must be run from within a polecat worktree. Pushes the branch and, by
    default, sets the task status to 'merge_ready' and files a normal PR.

    With ``--partial`` the work is an honest-incomplete stop: the PR is filed
    as a *draft* and the task is released as 'partial' rather than
    'merge_ready', so it is visible as not-yet-mergeable to the reviewer. This
    is the partial-work terminal state — a whole smaller thing, cut at a scope
    seam, disclosed via a ``## Deliberately deferred`` PR section, with a live
    follow-up task carrying the remainder.
    """
    import subprocess

    # Lazy imports of helpers that still live in cli.py — avoids the import
    # cycle that would result from a top-level ``from polecat.cli import ...``
    # (cli.py imports finalize at module load to register the command).
    from polecat.cli import (
        TRANSCRIPT_TASK_BODY_HEADER,
        _check_gh_installed,
        _format_transcript_task_body_section,
        _generate_pr_body,
        _read_latest_real_transcript_path,
    )

    if branch:
        os.environ["AOPS_POLECAT_BRANCH"] = branch

    manager = PolecatManager(home_dir=ctx.obj.get("home"), verbose=ctx.obj.get("verbose", False))
    cwd = Path.cwd()

    # Detect if we're in a polecat worktree
    if not cwd.is_relative_to(manager.polecats_dir):
        print(
            f"Error: Not in a polecat worktree. Expected path under {manager.polecats_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract task ID from directory name
    task_id = cwd.relative_to(manager.polecats_dir).parts[0]
    if manager.storage is not None:
        task = manager.storage.get_task(task_id)
    else:
        from polecat.pkb_bridge import get_task as pkb_get_task

        task = pkb_get_task(task_id)

    if not task:
        print(f"Error: Task {task_id} not found in task database", file=sys.stderr)
        sys.exit(1)

    # CLI --project/-p overrides task.project
    _target_project = project or task.project
    if _target_project:
        try:
            task.project = manager.resolve_project_alias(_target_project)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Resolve the base branch — the rebase target AND the PR base — from the
    # project registry (academicOps → dev, external repos → their own default),
    # honouring a per-task override. Replaces the legacy hardcoded `dev`, which
    # was correct only for academicOps and broke cross-repo dispatch: a worker
    # finalizing against overwhelm-dashboard (default `main`, no `dev` branch)
    # would `git fetch origin dev` / open a PR `--base dev` and fail.
    base_branch = getattr(task, "base_branch", None) or manager.default_branch_for(task.project)
    base_branch = str(base_branch).strip()
    origin_ref = f"origin/{base_branch}"

    # --- SAFEGUARD 0: Completion Protection ---
    # If the task is already DONE, or in review/merge phase, do NOT override it.
    # This prevents the "infinite retry loop" where auto-finish resets a manually completed task.
    # 'partial' is terminal for the worker too: an honest partial stop ships a
    # draft PR + follow-up task and must NOT be reset by the auto-retry loop.
    _TERMINAL_STATUSES = ("done", "review", "merge_ready", "cancelled", "partial")
    try:
        from lib.task_model import TaskStatus

        terminal_or_pr_statuses = tuple(
            s
            for s in (
                getattr(TaskStatus, "DONE", None),
                getattr(TaskStatus, "REVIEW", None),
                getattr(TaskStatus, "MERGE_READY", None),
                getattr(TaskStatus, "CANCELLED", None),
                getattr(TaskStatus, "PARTIAL", None),
            )
            if s is not None
        )

        if task.status in terminal_or_pr_statuses:
            print(f"✅ Task {task_id} is in status '{task.status}'. Skipping auto-retry reset.")
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())  # Move out of worktree before nuking
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            return
    except ImportError:
        status_str = task.status or ""
        if status_str in _TERMINAL_STATUSES:
            print(f"✅ Task {task_id} is in status '{status_str}'. Skipping auto-retry reset.")
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            return

    print(f"Finishing task: {task.title} ({task_id})")

    # --- SAFEGUARD 1: Dirty Exit Protection ---
    # Check for uncommitted changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Warning: Uncommitted changes detected.")
        # Automatically commit changes if they are simple
        print("  🧹 Automatically staging and committing changes...")
        try:
            subprocess.run(["git", "add", "-u"], check=True)  # Stage modified/deleted
            subprocess.run(["git", "add", "."], check=True)  # Stage new files (careful!)
            subprocess.run(
                ["git", "commit", "-m", "chore: saving uncommitted agent work"],
                check=True,
            )
            print("  ✅ Changes saved.")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to auto-commit: {e}")
            if not force:
                print(
                    "  🚫 Uncommitted changes could not be saved. Use --force to continue anyway."
                )
                sys.exit(1)

    # --- NO-CHANGES DETECTION ---
    # If the agent made no changes, the task was likely not completed (e.g., stuck in
    # hydration loop, crashed early, or other failure mode). Do NOT mark as done.
    # See: aops-91e4c3f2 - Gemini polecat workers stuck in hydration gate loop
    try:
        # First, fetch to ensure we have the latest base branch
        subprocess.run(
            ["git", "fetch", "origin", base_branch],
            capture_output=True,
            check=False,
        )
        # Check if there are any commits on this branch vs the base branch
        diff_check = subprocess.run(
            ["git", "diff", "--quiet", origin_ref, "HEAD"],
            capture_output=True,
            check=False,
        )
        # git diff --quiet returns 0 if no changes, 1 if changes exist
        if diff_check.returncode == 0:
            if force_done:
                print("📭 No changes detected, but --force-done specified.")
                print("✅ Proceeding to mark as DONE (verified complete without changes).")
                _finish_evidence = f"{task.title} — completed without code changes (--force-done)"
                from polecat.pkb_bridge import complete_task as pkb_complete

                pkb_complete(task_id, completion_evidence=_finish_evidence)
                print(f"✅ Task {task_id} marked as DONE.")

                # Optionally nuke
                if do_nuke:
                    print("Nuking worktree...")
                    os.chdir(Path.home())  # Move out of worktree before nuking
                    manager.nuke_worktree(task_id, force=True)
                    print("Worktree removed")
                else:
                    print(f"\nTo clean up later: polecat nuke {task_id}")
                return  # Exit early, task is DONE
            else:
                print("📭 No changes detected. Worker may not have completed the task.")
                print(
                    "⚠️  Marking as 'review' for investigation (use --force-done for legitimate zero-change tasks)."
                )
                # Mark task as REVIEW, NOT active (avoid infinite re-queue for non-code tasks)
                # Zero changes needs human/supervisor judgment — could be failure OR legitimate
                task.status = "review"
                task.assignee = None
                task.body = (
                    (task.body or "")
                    + "\n\n## ⚠️ Review needed (zero changes detected)\n"
                    + "Worker finished without making changes. Needs investigation:\n"
                    + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                    + "- If the worker failed silently, check transcript and retry\n"
                )
                try:
                    from lib.task_model import TaskStatus

                    task.status = TaskStatus.REVIEW
                    manager.storage.save_task(task)  # pyright: ignore[reportOptionalMemberAccess]
                except ImportError:
                    from polecat.pkb_bridge import save_task as pkb_save

                    pkb_save(task)
                print("📋 Task sent to review queue")

                # Optionally nuke
                if do_nuke:
                    print("Nuking worktree...")
                    os.chdir(Path.home())  # Move out of worktree before nuking
                    manager.nuke_worktree(task_id, force=False)
                    print("Worktree removed")
                else:
                    print(f"\nTo clean up later: polecat nuke {task_id}")
                return  # Exit early, skip rest of finish flow

    except Exception as e:
        print(f"Warning: Could not check for changes against {origin_ref}: {e}")
        # Fallback: try the local base-branch ref instead of origin/<base>
        try:
            diff_local = subprocess.run(
                ["git", "diff", "--quiet", base_branch, "HEAD"],
                capture_output=True,
                check=False,
            )
            if diff_local.returncode == 0:
                # Zero changes confirmed via local base-branch ref
                if force_done:
                    print(
                        f"📭 No changes detected (local {base_branch} fallback), but --force-done specified."
                    )
                    print("✅ Proceeding to mark as DONE (verified complete without changes).")
                    _finish_evidence = (
                        f"{task.title} — completed without code changes (--force-done)"
                    )
                    from polecat.pkb_bridge import complete_task as pkb_complete

                    pkb_complete(task_id, completion_evidence=_finish_evidence)
                    print(f"✅ Task {task_id} marked as DONE.")
                    if do_nuke:
                        print("Nuking worktree...")
                        os.chdir(Path.home())
                        manager.nuke_worktree(task_id, force=True)
                        print("Worktree removed")
                    else:
                        print(f"\nTo clean up later: polecat nuke {task_id}")
                    return
                else:
                    print(
                        f"📭 No changes detected (local {base_branch} fallback). Worker may not have completed the task."
                    )
                    print(
                        "⚠️  Marking as 'review' for investigation (use --force-done for legitimate zero-change tasks)."
                    )
                    task.assignee = None
                    task.body = (
                        (task.body or "")
                        + "\n\n## ⚠️ Review needed (zero changes detected)\n"
                        + "Worker finished without making changes. Needs investigation:\n"
                        + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                        + "- If the worker failed silently, check transcript and retry\n"
                    )
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.REVIEW.value
                        manager.storage.save_task(task)  # pyright: ignore[reportOptionalMemberAccess]
                    except ImportError:
                        from polecat.pkb_bridge import save_task as pkb_save

                        task.status = "review"
                        pkb_save(task)
                    print("📋 Task sent to review queue")
                    if do_nuke:
                        print("Nuking worktree...")
                        os.chdir(Path.home())
                        manager.nuke_worktree(task_id, force=False)
                        print("Worktree removed")
                    else:
                        print(f"\nTo clean up later: polecat nuke {task_id}")
                    return
            # else: diff_local.returncode != 0 means changes exist, fall through to normal flow
        except Exception as e2:
            print(f"Warning: Fallback change detection also failed: {e2}")
            # Both origin and local base-branch comparisons failed — needs human investigation
            print("⚠️  Cannot verify changes exist. Marking as 'review' (safe default).")
            task.assignee = None
            task.body = (
                (task.body or "")
                + "\n\n## ⚠️ Review needed (change detection failed)\n"
                + f"Could not compare against {base_branch} to determine if worker made changes.\n"
                + "- If the task legitimately requires no code changes, re-run with `--force-done`\n"
                + "- If the worker failed silently, check transcript and retry\n"
            )
            try:
                from lib.task_model import TaskStatus

                task.status = TaskStatus.REVIEW.value
                manager.storage.save_task(task)  # pyright: ignore[reportOptionalMemberAccess]
            except ImportError:
                from polecat.pkb_bridge import save_task as pkb_save

                task.status = "review"
                pkb_save(task)
            print("📋 Task sent to review queue")
            if do_nuke:
                print("Nuking worktree...")
                os.chdir(Path.home())
                manager.nuke_worktree(task_id, force=False)
                print("Worktree removed")
            else:
                print(f"\nTo clean up later: polecat nuke {task_id}")
            return

    # --- SAFEGUARD 2: Repo-Nuke Protection ---
    # Check if we are unexpectedly rewriting the whole repo
    # This prevents the "orphan branch" issue where an agent commits 1000+ files as new
    try:
        # Get shortstat diff against the base branch to see scale of changes
        diff_res = subprocess.run(
            ["git", "diff", "--shortstat", origin_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Output format: " 10 files changed, 100 insertions(+), 50 deletions(-)"
        if diff_res.returncode == 0 and diff_res.stdout.strip():
            parts = diff_res.stdout.strip().split(",")
            files_changed_str = parts[0].strip().split(" ")[0]
            if files_changed_str.isdigit():
                files_changed = int(files_changed_str)
                if files_changed > 50:
                    print(
                        f"\n🚨 SAFEGUARD ACTIVATE: Large changeset detected ({files_changed} files)."
                    )
                    print("   This looks like a 'repo nuke' or orphan branch issue.")
                    print("   Run 'git reset --soft FETCH_HEAD' to recover if this is accidental.")
                    if not force:
                        print(
                            "   🚫 Large changeset requires confirmation. Use --force to push anyway."
                        )
                        sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not run repo checking safeguards: {e}")

    # Push to origin
    if not no_push:
        # Determine the current git branch checked out in the worktree
        git_branch = None
        try:
            git_branch_res = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            if git_branch_res.returncode == 0 and git_branch_res.stdout.strip():
                git_branch = git_branch_res.stdout.strip()
        except Exception as e:
            print(f"Warning: Could not determine current git branch: {e}")

        # Resolve branch name. Delegate the canonical priority ladder
        # (env override -> task frontmatter -> config -> default) to the single
        # source of truth on the manager, then apply the finalize-only fallback:
        # the branch currently checked out in this worktree, used only when the
        # canonical resolver fell through to its default branch-per-task sentinel.
        branch_name = manager.resolve_branch_name(task)
        if branch_name == f"polecat/{task_id}" and git_branch:
            branch_name = git_branch

        is_shared = manager.is_shared_branch(branch_name, task_id)

        # --- SAFEGUARD 3: Main-Push Blockade ---
        if branch_name == "main" or branch_name == "master":
            print("🚨 SAFEGUARD: Refusing to push 'main' branch via polecat.")
            sys.exit(1)

        if is_shared:
            # Check if remote shared branch exists
            branch_exists = False
            try:
                ls_remote = subprocess.run(
                    ["git", "ls-remote", "--heads", "origin", branch_name],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                branch_exists = bool(ls_remote.stdout.strip())
            except subprocess.CalledProcessError as e:
                # Don't silently swallow: surface the probe failure so an
                # unreachable / unauthenticated origin is visible. Continue
                # (treating the branch as absent) rather than hard-aborting —
                # if origin is genuinely unreachable the downstream push will
                # fail loudly with a clear error.
                print(
                    f"  ⚠️  Could not probe remote for shared branch {branch_name} "
                    f"(git ls-remote failed): {e.stderr or e}",
                    file=sys.stderr,
                )

            if branch_exists:
                print(f"🔄 Syncing with remote shared branch {branch_name}...")
                subprocess.run(
                    ["git", "fetch", "origin", branch_name],
                    check=True,
                    capture_output=True,
                )
                print(f"  📥 Rebasing local commits onto origin/{branch_name}...")
                rebase_result = subprocess.run(
                    ["git", "rebase", f"origin/{branch_name}"],
                    capture_output=True,
                    text=True,
                )
                if rebase_result.returncode != 0:
                    subprocess.run(["git", "rebase", "--abort"], check=False)
                    print(
                        f"  ❌ Rebase onto origin/{branch_name} failed due to conflicts.",
                        file=sys.stderr,
                    )
                    print(f"  {rebase_result.stderr}", file=sys.stderr)
                    print("  Task will be marked for review.", file=sys.stderr)
                    task.body += f"\n\n## ⚠️ Rebase Failed\nConflicts detected during rebase onto shared branch {branch_name}.\n"
                    try:
                        from lib.task_model import TaskStatus

                        task.status = TaskStatus.REVIEW.value
                    except ImportError:
                        task.status = "review"
                    # manager.save_task is the None-safe SSOT wrapper: it routes
                    # to storage when present and falls back to the pkb bridge
                    # otherwise (manager.py:save_task).
                    manager.save_task(task)
                    sys.exit(1)
                print("  ✅ Rebase onto remote shared branch successful")
        else:
            # --- REBASE BEFORE PUSH (default branch-per-task) ---
            # Fetch and rebase onto the latest base branch to prevent orphan commits
            # and merge conflicts
            print(f"🔄 Syncing with latest {base_branch} before push...")
            try:
                # Fetch latest from origin
                subprocess.run(
                    ["git", "fetch", "origin", base_branch],
                    check=True,
                    capture_output=True,
                )

                # Check if we need to rebase (are we behind the base branch?)
                merge_base = subprocess.run(
                    ["git", "merge-base", "HEAD", origin_ref],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                origin_base = subprocess.run(
                    ["git", "rev-parse", origin_ref],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if merge_base.stdout.strip() != origin_base.stdout.strip():
                    # We're behind, need to rebase
                    print(f"  📥 Branch is behind {origin_ref}, rebasing...")
                    rebase_result = subprocess.run(
                        ["git", "rebase", origin_ref],
                        capture_output=True,
                        text=True,
                    )
                    if rebase_result.returncode != 0:
                        # Rebase failed - abort and report
                        subprocess.run(["git", "rebase", "--abort"], check=False)
                        print("  ❌ Rebase failed due to conflicts.", file=sys.stderr)
                        print(f"  {rebase_result.stderr}", file=sys.stderr)
                        print("  Task will be marked for review.", file=sys.stderr)
                        # Don't exit - let it fall through to mark as review
                        task.body += f"\n\n## ⚠️ Rebase Failed\nConflicts detected during rebase onto {base_branch}.\n"
                        try:
                            from lib.task_model import TaskStatus

                            task.status = TaskStatus.REVIEW.value
                        except ImportError:
                            task.status = "review"
                        manager.save_task(task)
                        sys.exit(1)
                    print("  ✅ Rebase successful")
                else:
                    print(f"  ✅ Already up-to-date with {base_branch}")

            except subprocess.CalledProcessError as e:
                print(f"  ⚠️ Sync failed: {e}", file=sys.stderr)
                # Continue anyway - the push might still work

        print(f"Pushing {branch_name} to origin...")
        try:
            # Fetch the branch tracking ref so --force-with-lease has current data.
            # Without this, rebase leaves the local tracking ref stale and push
            # is rejected with "(stale info)".
            subprocess.run(
                ["git", "fetch", "origin", branch_name],
                check=False,
                capture_output=True,
            )
            # Use --force-with-lease for shared branches, --force for non-shared branches
            push_args = ["git", "push"]
            if is_shared:
                push_args.append("--force-with-lease")
            else:
                push_args.append("--force")
            push_args.extend(["-u", "origin", f"{branch_name}:{branch_name}"])
            subprocess.run(push_args, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to origin: {e}", file=sys.stderr)
            sys.exit(1)

    # --- Surface real transcript path (task-91c5058f) ---
    # Read the most recent real_transcript_path from the polecat stub, then:
    #   1. Append it to the task body so the path lives in the PKB record.
    #   2. Pass it to _generate_pr_body so reviewers see it on the PR.
    transcript_path = _read_latest_real_transcript_path(task_id, manager.home_dir)
    if transcript_path:
        if TRANSCRIPT_TASK_BODY_HEADER not in (task.body or ""):
            task.body = (task.body or "") + _format_transcript_task_body_section(transcript_path)
            try:
                manager.save_task(task)
            except Exception as e:
                print(f"  ⚠️  Could not persist transcript path to task body: {e}")

    # --- GitHub PR Integration ---
    try:
        if _check_gh_installed():
            print("  🐙 GitHub CLI detected. Updating Pull Request...")
            pr_body = _generate_pr_body(task, transcript_path=transcript_path)

            # Create a temp file for the body to handle multiline content safely
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(pr_body)
                body_file = f.name

            try:
                # Check if PR exists
                pr_check = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "list",
                        "--head",
                        branch_name,
                        "--json",
                        "number",
                        "--state",
                        "open",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                prs = []
                if pr_check.returncode == 0 and pr_check.stdout.strip():
                    try:
                        prs = json.loads(pr_check.stdout)
                    except json.JSONDecodeError:
                        pass

                if prs:
                    # Update existing PR
                    pr_number = prs[0]["number"]
                    subprocess.run(
                        ["gh", "pr", "edit", str(pr_number), "--body-file", body_file],
                        check=True,
                        capture_output=True,
                    )
                    print(f"  ✅ Updated PR #{pr_number}")
                else:
                    # Create new PR. A partial stop files a DRAFT PR — GitHub
                    # enforces not-mergeable on drafts, so a `partial` task can
                    # never satisfy the APPROVED-on-SHA merge trigger by accident.
                    create_args = [
                        "gh",
                        "pr",
                        "create",
                        "--title",
                        task.title,
                        "--body-file",
                        body_file,
                        "--head",
                        branch_name,
                        "--base",
                        base_branch,
                    ]
                    if is_partial:
                        create_args.append("--draft")
                    subprocess.run(create_args, check=True, capture_output=True)
                    print("  ✅ Created new draft PR" if is_partial else "  ✅ Created new PR")

            except subprocess.CalledProcessError as e:
                # Don't fail the whole finish command if PR creation fails
                err_msg = e.stderr.decode().strip() if e.stderr else str(e)
                print(f"  ⚠️  Failed to manage PR: {err_msg}")
            except Exception as e:
                print(f"  ⚠️  Error in PR integration: {e}")
            finally:
                if os.path.exists(body_file):
                    os.unlink(body_file)

    except Exception as e:
        print(f"  ⚠️  Unexpected error in PR integration: {e}")

    # Release task with summary via PKB release_task
    # Auto-generate summary from git diff stats
    finish_summary = task.title
    try:
        stat_res = subprocess.run(
            ["git", "diff", "--shortstat", origin_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if stat_res.returncode == 0 and stat_res.stdout.strip():
            finish_summary = f"{task.title}. Changes: {stat_res.stdout.strip()}"
    except Exception as e:
        print(f"  ⚠️  Could not generate git diff summary: {e}", file=sys.stderr)

    # Try to get PR URL
    pr_url_str = None
    try:
        pr_res = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch_name,
                "--state",
                "open",
                "--json",
                "url",
                "-q",
                ".[0].url",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if pr_res.returncode == 0 and pr_res.stdout.strip():
            pr_url_str = pr_res.stdout.strip()
    except Exception as e:
        print(f"  ⚠️  Could not get PR URL: {e}", file=sys.stderr)

    target_status = "partial" if is_partial else "merge_ready"
    released_ok = False
    try:
        from polecat.pkb_bridge import release_task as pkb_release

        released = pkb_release(
            task_id,
            status=target_status,
            summary=finish_summary,
            pr_url=pr_url_str,
            branch=branch_name,
        )
        if not released:
            raise RuntimeError("release_task returned False")
        released_ok = True
    except Exception as _release_exc:
        from polecat.validation import PRURLValidationError as _PRURLValidationError

        if isinstance(_release_exc, _PRURLValidationError):
            print(f"  ❌  A3/A8 integrity gate — pr_url rejected: {_release_exc}", file=sys.stderr)
            sys.exit(1)

        # A `partial` stop must NEVER be laundered into `merge_ready`: that would
        # convert an honest-incomplete stop into a false completion claim
        # (clause-2b illegal-gap). If the PKB does not yet accept `partial` as a
        # status (server-side enum not extended), leave the task non-terminal and
        # hand off via the draft PR + follow-up task instead of falling back.
        if is_partial:
            print(
                f"  ⚠️  Could not release task as 'partial': {_release_exc}",
                file=sys.stderr,
            )
            print(
                "  ↪︎ The draft PR and follow-up task carry the partial hand-off. "
                "Leaving task non-terminal — refusing to mark 'merge_ready' "
                "(that would falsely claim completion).",
                file=sys.stderr,
            )
        else:
            # merge_ready fallback path if release_task is unavailable.
            try:
                from lib.task_model import TaskStatus

                task.status = TaskStatus.MERGE_READY.value
                manager.storage.save_task(task)  # pyright: ignore[reportOptionalMemberAccess]
                released_ok = True
            except ImportError:
                from polecat.pkb_bridge import save_task as pkb_save

                task.status = "merge_ready"
                pkb_save(task)
                released_ok = True

    if is_partial:
        if released_ok:
            print("✅ Task marked as 'partial' (honest partial stop)")
        print(
            "📋 Draft PR filed. The remainder lives in the follow-up task; this work "
            "is not a merge candidate until promoted."
        )
    else:
        print("✅ Task marked as 'merge_ready'")
        print(
            "📋 If a PR was created, the review pipeline will handle merge. "
            "See logs above for PR status."
        )

    # Optionally nuke
    if do_nuke:
        print("Nuking worktree...")
        os.chdir(Path.home())  # Move out of worktree before nuking
        # Branch was pushed and PR filed; merge check no longer applies here
        manager.nuke_worktree(task_id, force=True)
        print("Worktree removed")
    else:
        print(f"\nTo clean up later: polecat nuke {task_id}")
