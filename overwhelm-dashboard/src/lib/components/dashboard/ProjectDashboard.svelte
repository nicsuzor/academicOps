<script lang="ts">
    export let projectProjects: string[] = [];
    export let projectData: any = {};

    $: hasData = projectProjects && projectProjects.length > 0;
</script>

{#if hasData}
    <div class="project-dashboard">
        {#each projectProjects as project}
            {@const meta = projectData.meta?.[project] || {}}
            {@const tasks = projectData.tasks?.[project] || []}
            {@const accomplishments =
                projectData.accomplishments?.[project] || []}
            {@const sessions = projectData.sessions?.[project] || []}

            {#if tasks.length > 0 || accomplishments.length > 0 || sessions.length > 0}
                <div class="project-section">
                    <div class="project-header">
                        <h3 class="project-title">
                            <span class="icon">📁</span>
                            {project}
                            {#if meta.is_spotlight}
                                <span class="spotlight-badge"
                                    >★ SPOTLIGHT EPIC</span
                                >
                            {/if}
                        </h3>
                    </div>

                    <div class="project-content">
                        {#if meta.epics && meta.epics.length > 0}
                            <div class="epics-list">
                                {#each meta.epics as epic}
                                    <div class="epic-card">
                                        <div class="epic-header">
                                            <span class="epic-title"
                                                >{epic.title}</span
                                            >
                                            {#if epic.progress}
                                                <span class="epic-progress"
                                                    >{epic.progress
                                                        .completed}/{epic
                                                        .progress.total}</span
                                                >
                                            {/if}
                                        </div>
                                        {#if epic.progress && epic.progress.total > 0}
                                            <div class="progress-bar">
                                                <div
                                                    class="progress-fill"
                                                    style="width: {(epic
                                                        .progress.completed /
                                                        epic.progress.total) *
                                                        100}%"
                                                ></div>
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        {/if}

                        <div class="columns">
                            <div class="col active-tasks">
                                <h4 class="col-title">Active Tasks</h4>
                                {#each tasks as task}
                                    <div class="task-item">
                                        <span class="priority p{task.priority}"
                                            >P{task.priority}</span
                                        >
                                        <span class="task-title"
                                            >{task.title}</span
                                        >
                                        {#if task.status === "in_progress"}
                                            <span class="status-badge running"
                                                >Running</span
                                            >
                                        {/if}
                                    </div>
                                {:else}
                                    <div class="empty">No active tasks.</div>
                                {/each}
                            </div>

                            <div class="col recent-done">
                                <h4 class="col-title">Recently Completed</h4>
                                {#each accomplishments as acc}
                                    <div class="acc-item">
                                        <span class="check">✓</span>
                                        <span class="acc-desc"
                                            >{acc.description}</span
                                        >
                                    </div>
                                {:else}
                                    <div class="empty">
                                        Nothing recently completed.
                                    </div>
                                {/each}
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        {/each}
    </div>
{/if}

<style>
    .panel {
        background: var(--bg-panel);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 24px;
        box-shadow: var(--shadow-md);
    }

    .project-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        border-bottom: 1px solid var(--border-subtle);
        padding-bottom: 16px;
    }

    .project-title {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .epic-badge {
        background: rgba(129, 140, 248, 0.1);
        color: var(--accent-primary);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 1px solid rgba(129, 140, 248, 0.2);
    }

    .section-title {
        color: var(--text-muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 700;
        margin: 0 0 16px 0;
    }

    .group {
        margin-bottom: 28px;
    }
    .group:last-child {
        margin-bottom: 0;
    }

    .cards-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .task-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 16px;
        transition:
            transform var(--transition-fast),
            box-shadow var(--transition-fast);
    }

    .task-card:hover {
        transform: translateX(4px);
        box-shadow: var(--shadow-sm);
        border-color: rgba(255, 255, 255, 0.1);
    }

    .card-title {
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .card-meta {
        display: flex;
        gap: 12px;
        font-size: 12px;
        color: var(--text-muted);
        align-items: center;
    }

    .owner {
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 8px;
        border-radius: 12px;
        color: var(--text-secondary);
    }

    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--text-muted);
    }

    .dot.active {
        background: var(--accent-success);
        box-shadow: 0 0 8px rgba(52, 211, 153, 0.4);
    }
    .dot.blocked {
        background: var(--accent-danger);
        box-shadow: 0 0 8px rgba(248, 113, 113, 0.4);
    }
    .dot.done {
        background: var(--accent-primary);
    }

    .accomplishment-card {
        background: linear-gradient(
            135deg,
            rgba(52, 211, 153, 0.05),
            transparent
        );
        border: 1px solid rgba(52, 211, 153, 0.1);
        border-left: 3px solid var(--accent-success);
        border-radius: var(--radius-md);
        padding: 16px;
        transition: transform var(--transition-fast);
    }

    .accomplishment-card:hover {
        transform: translateX(4px);
    }

    .acc-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .acc-title {
        color: var(--accent-success);
        font-weight: 600;
        font-size: 14px;
    }

    .time {
        color: var(--text-muted);
        font-size: 12px;
        font-variant-numeric: tabular-nums;
    }

    .priority {
        font-size: 10px;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 3px;
        background: var(--bg-input);
        color: var(--text-secondary);
    }

    .priority.p0 {
        background: var(--accent-danger);
        color: white;
    }
    .priority.p1 {
        background: var(--accent-warning);
        color: var(--bg-app);
    }
    .priority.p2 {
        background: var(--accent-success);
        color: var(--bg-app);
    }

    .task-title {
        color: #e2e8f0;
        font-size: 13px;
        flex: 1;
    }

    .status-badge {
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 10px;
        background: rgba(74, 222, 128, 0.1);
        color: #4ade80;
        border: 1px solid rgba(74, 222, 128, 0.2);
    }

    .acc-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 6px 0;
        font-size: 13px;
    }

    .check {
        color: #4ade80;
        font-weight: bold;
    }

    .acc-desc {
        color: #94a3b8;
        line-height: 1.4;
    }

    .empty {
        color: #64748b;
        font-size: 13px;
        font-style: italic;
    }
</style>
