<script lang="ts">
    export let leftOff: any;

    $: active = leftOff?.active || [];
    $: paused = leftOff?.paused || [];
</script>

<div class="panel where-you-left-off">
    <h3 class="section-header">WHERE YOU LEFT OFF</h3>

    {#if active.length === 0 && paused.length === 0}
        <div class="empty">No recent sessions found.</div>
    {/if}

    {#if active.length > 0}
        <div class="bucket">
            <h4 class="bucket-title">🟢 Active (last 4h)</h4>
            <div class="cards">
                {#each active as session}
                    <div class="session-card">
                        <div class="card-header">
                            <span class="project">{session.project}</span>
                            <span class="time">{session.time_display}</span>
                        </div>
                        <div class="goal">
                            {session.goal || session.description}
                        </div>

                        {#if session.now_task}
                            <div class="todo now-task">
                                <span class="indicator">▶</span>
                                {session.now_task}
                            </div>
                        {/if}

                        {#if session.next_task}
                            <div class="todo next-task">
                                <span class="indicator">⏳</span>
                                {session.next_task}
                            </div>
                        {/if}

                        {#if session.progress_total > 0}
                            <div class="progress-container">
                                <div class="progress-bar">
                                    <div
                                        class="progress-fill"
                                        style="width: {(session.progress_done /
                                            session.progress_total) *
                                            100}%"
                                    ></div>
                                </div>
                                <span class="progress-text"
                                    >{session.progress_done}/{session.progress_total}</span
                                >
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        </div>
    {/if}

    {#if paused.length > 0}
        <div class="bucket">
            <h4 class="bucket-title paused-title">🟡 Paused (4-24h)</h4>
            <div class="cards">
                {#each paused as session}
                    <div class="session-card paused-card">
                        <div class="card-header">
                            <span class="project">{session.project}</span>
                            <span class="time">{session.time_display}</span>
                        </div>
                        <div class="goal">
                            {session.goal || session.description}
                        </div>
                        {#if session.outcome_text}
                            <div class="outcome {session.outcome_class}">
                                {session.outcome_text}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>

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

    .section-header {
        color: var(--text-muted);
        font-size: 13px;
        letter-spacing: 0.1em;
        margin: 0 0 20px 0;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-subtle);
        text-transform: uppercase;
        font-weight: 700;
    }

    .bucket {
        margin-bottom: 28px;
    }
    .bucket:last-child {
        margin-bottom: 0;
    }

    .bucket-title {
        color: var(--text-primary);
        font-size: 14px;
        margin: 0 0 16px 0;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .paused-title {
        color: var(--text-secondary);
    }

    .cards {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .session-card {
        background: var(--bg-card);
        border-left: 4px solid var(--accent-primary);
        border-radius: var(--radius-md);
        padding: 16px;
        transition:
            transform var(--transition-fast),
            box-shadow var(--transition-fast);
    }

    .session-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .paused-card {
        border-left-color: var(--text-muted);
        background: rgba(39, 39, 42, 0.3);
        opacity: 0.9;
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        align-items: center;
    }

    .project {
        font-weight: 700;
        color: var(--accent-primary);
        font-size: 13px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .paused-card .project {
        color: var(--text-secondary);
    }

    .time {
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 500;
    }

    .goal {
        color: var(--text-primary);
        font-size: 14px;
        margin-bottom: 12px;
        line-height: 1.5;
        font-weight: 500;
    }

    .todo {
        font-size: 13px;
        padding: 6px 12px;
        border-radius: var(--radius-sm);
        margin-bottom: 6px;
        display: flex;
        gap: 10px;
        align-items: center;
        font-weight: 500;
    }

    .now-task {
        background: rgba(52, 211, 153, 0.1);
        color: var(--accent-success);
        border: 1px solid rgba(52, 211, 153, 0.2);
    }

    .next-task {
        background: rgba(251, 191, 36, 0.05);
        color: var(--accent-warning);
        border: 1px solid rgba(251, 191, 36, 0.1);
    }

    .indicator {
        font-size: 10px;
    }

    .progress-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 16px;
    }

    .progress-bar {
        flex: 1;
        height: 6px;
        background: var(--bg-input);
        border-radius: 3px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent-success), #10b981);
        border-radius: 3px;
    }

    .progress-text {
        color: var(--text-muted);
        font-size: 12px;
        font-variant-numeric: tabular-nums;
        font-weight: 600;
    }

    .outcome {
        display: inline-block;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: var(--radius-sm);
        margin-top: 10px;
    }

    .outcome.success,
    .outcome.merged {
        background: rgba(52, 211, 153, 0.1);
        color: var(--accent-success);
        border: 1px solid rgba(52, 211, 153, 0.2);
    }

    .outcome.needs {
        background: rgba(251, 191, 36, 0.1);
        color: var(--accent-warning);
        border: 1px solid rgba(251, 191, 36, 0.2);
    }

    .outcome.failure {
        background: rgba(248, 113, 113, 0.1);
        color: var(--accent-danger);
        border: 1px solid rgba(248, 113, 113, 0.2);
    }

    .empty {
        color: var(--text-muted);
        font-style: italic;
        font-size: 14px;
        padding: 24px 0;
        text-align: center;
    }
</style>
