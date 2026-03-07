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

<div class="flex flex-col gap-4 font-mono w-full">
    <div class="flex justify-between items-center border-b border-primary/30 pb-2">
        <h3 class="text-sm font-bold tracking-widest text-primary flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px]">bolt</span>
            CURRENT ACTIVITY ({sessions.length})
        </h3>
        {#if needsYou.length > 0}
            <div class="flex items-center gap-2 px-3 py-1 border border-red-500 bg-red-900/20 text-red-500 font-bold text-[10px] uppercase tracking-widest animate-pulse">
                <span class="material-symbols-outlined text-[14px]">warning</span>
                {needsYou.length} Needs You
            </div>
        {/if}
    </div>

    <div class="flex flex-col gap-2">
        {#each sessions.slice(0, 5) as session}
            <div class="flex items-center gap-4 bg-primary/5 border-l-2 border-primary/50 p-2 hover:bg-primary/10 transition-colors cursor-default">
                <span class="text-[10px] text-primary/60 min-w-[55px]">{formatTimeAgo(session.started_at)}</span>
                {#if session.project}
                    <span class="text-[10px] font-bold bg-primary/20 text-primary px-2 py-0.5 border border-primary/20">{session.project}</span>
                {/if}
                <span class="text-xs text-primary/90 truncate flex-1" title={session.description}>
                    {session.description}
                </span>
            </div>
        {/each}
        {#if sessions.length === 0}
            <div class="text-xs text-primary/40 italic">No active agent sessions in the last hour.</div>
        {/if}
    </div>
</div>
