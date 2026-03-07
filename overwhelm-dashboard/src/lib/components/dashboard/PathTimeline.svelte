<script lang="ts">
    export let path: any;

    $: threads = path?.threads || [];
    $: abandoned = path?.abandoned_work || [];

    function formatTime(isoString: string): string {
        if (!isoString) return "";
        try {
            const d = new Date(isoString);
            return d.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch {
            return isoString;
        }
    }
</script>

{#if threads.length > 0 || abandoned.length > 0}
    <div class="panel path-panel">
        <h3 class="section-header">PATH RECONSTRUCTION</h3>

        {#if abandoned.length > 0}
            <div class="abandoned-section">
                <h4>⚠️ Abandoned Work Detected</h4>
                <div class="abandoned-list">
                    {#each abandoned as item}
                        <div class="abandoned-item">
                            <div class="meta">
                                <span class="project"
                                    >{item.project || "Unknown"}</span
                                >
                                <span class="time">{item.time_ago || ""}</span>
                            </div>
                            <div class="desc">{item.description}</div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        <div class="threads-timeline">
            {#each threads as thread}
                <div class="thread">
                    <div class="thread-header">
                        <span class="project">{thread.project}</span>
                        {#if thread.git_branch}
                            <span class="branch">⑂ {thread.git_branch}</span>
                        {/if}
                        <span class="session-id">{thread.session_id}</span>
                    </div>

                    {#if thread.initial_goal || thread.hydrated_intent}
                        <div class="intent">
                            <strong>Goal:</strong>
                            {thread.hydrated_intent || thread.initial_goal}
                        </div>
                    {/if}

                    <div class="events">
                        {#each thread.events as event}
                            <div class="event {event.event_type}">
                                <div class="event-time">
                                    {formatTime(event.timestamp)}
                                </div>
                                <div class="event-marker">
                                    <div class="dot"></div>
                                    <div class="line"></div>
                                </div>
                                <div class="event-content">
                                    <div class="narrative">
                                        {event.narrative}
                                    </div>
                                    {#if event.task_id}
                                        <div class="task-id">
                                            {event.task_id}
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
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

    h3 {
        color: var(--text-muted);
        font-size: 13px;
        letter-spacing: 0.1em;
        margin: 0 0 20px 0;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-subtle);
        text-transform: uppercase;
        font-weight: 700;
    }

    .timeline {
        position: relative;
        padding-left: 20px;
    }

    .timeline::before {
        content: "";
        position: absolute;
        left: 4px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: var(--border-subtle);
    }

    .event {
        position: relative;
        margin-bottom: 24px;
    }

    .event:last-child {
        margin-bottom: 0;
    }

    .intent {
        background: rgba(255, 255, 255, 0.05);
        padding: 10px 12px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-size: 13px;
        color: #e2e8f0;
        line-height: 1.4;
    }

    .intent strong {
        color: #94a3b8;
    }

    .event {
        display: flex;
        gap: 16px;
        position: relative;
    }

    .event-time {
        width: 60px;
        text-align: right;
        font-size: 12px;
        color: #64748b;
        padding-top: 2px;
    }

    .event-marker {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 12px;
    }

    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #3b82f6;
        margin-top: 6px;
        z-index: 1;
    }

    .event.git_commit .dot {
        background: #f59e0b;
    }
    .event.task_created .dot {
        background: #10b981;
    }
    .event.error .dot {
        background: #ef4444;
    }

    .line {
        width: 2px;
        flex: 1;
        background: #334155;
        margin-top: 4px;
    }

    .event:last-child .line {
        display: none;
    }

    .event-content {
        flex: 1;
        padding-bottom: 16px;
    }

    .narrative {
        font-size: 13px;
        color: #e2e8f0;
        line-height: 1.4;
    }

    .event.git_commit .narrative {
        color: #fcd34d;
        font-family: monospace;
    }

    .task-id {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
        font-family: monospace;
    }
</style>
