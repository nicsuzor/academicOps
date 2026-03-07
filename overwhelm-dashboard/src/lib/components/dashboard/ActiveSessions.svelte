<script lang="ts">
    export let sessions: any[] = [];
    export let needsYou: any[] = [];

    function formatTimeAgo(isoString: string): string {
        if (!isoString) return "just started";
        const date = new Date(isoString);
        const diffMs = Date.now() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHrs = Math.floor(diffMins / 60);
        return `${diffHrs}h ago`;
    }
</script>

<div class="panel current-activity-box">
    <div class="header">
        <h3>⚡ CURRENT ACTIVITY ({sessions.length})</h3>
        {#if needsYou.length > 0}
            <div class="needs-you-badge">
                <span class="icon">⚠️</span>
                <span>{needsYou.length} Needs You</span>
            </div>
        {/if}
    </div>

    <div class="sessions-list">
        {#each sessions.slice(0, 5) as session}
            <div class="session-row">
                <span class="ca-time">{formatTimeAgo(session.started_at)}</span>
                {#if session.project}
                    <span class="ca-project">{session.project}</span>
                {/if}
                <span class="ca-desc" title={session.description}>
                    {#if session.description.length > 120}
                        {session.description.substring(0, 120)}...
                    {:else}
                        {session.description}
                    {/if}
                </span>
            </div>
        {/each}
        {#if sessions.length === 0}
            <div class="empty">No active agent sessions in the last hour.</div>
        {/if}
    </div>
</div>

<style>
    .panel {
        background: var(--bg-panel);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px 24px;
        box-shadow: var(--shadow-md);
    }

    .current-activity-box {
        border-left: 4px solid var(--accent-success);
        background: linear-gradient(
            135deg,
            rgba(52, 211, 153, 0.05),
            transparent
        );
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    h3 {
        margin: 0;
        font-size: 13px;
        color: var(--accent-success);
        letter-spacing: 0.1em;
        font-weight: 700;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .needs-you-badge {
        background: rgba(248, 113, 113, 0.1);
        border: 1px solid rgba(248, 113, 113, 0.2);
        color: var(--accent-danger);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 8px rgba(248, 113, 113, 0.15);
        animation: pulse-border 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    @keyframes pulse-border {
        0%,
        100% {
            border-color: rgba(248, 113, 113, 0.2);
        }
        50% {
            border-color: rgba(248, 113, 113, 0.6);
        }
    }

    .sessions-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .session-row {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 14px;
        padding: 10px 12px;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid transparent;
        transition: all var(--transition-fast);
    }

    .session-row:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.08);
        transform: translateX(4px);
    }

    .ca-time {
        color: var(--text-muted);
        font-variant-numeric: tabular-nums;
        font-size: 12px;
        font-weight: 500;
        min-width: 55px;
    }

    .ca-project {
        background: rgba(129, 140, 248, 0.1);
        color: var(--accent-primary);
        padding: 4px 8px;
        border-radius: 6px;
        font-family: "JetBrains Mono", monospace;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    .ca-desc {
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        font-weight: 500;
    }

    .empty {
        color: var(--text-muted);
        font-size: 13px;
        font-style: italic;
        padding: 12px 0;
    }
</style>
