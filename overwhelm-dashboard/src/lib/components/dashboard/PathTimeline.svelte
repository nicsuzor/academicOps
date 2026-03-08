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
    <div class="flex flex-col gap-6 font-mono text-primary">
        <h3 class="text-xs font-bold tracking-[0.2em] text-primary/80 border-b border-primary/30 pb-2">PATH RECONSTRUCTION</h3>

        {#if abandoned.length > 0}
            <div class="flex flex-col gap-3 p-4 border border-yellow-500/30 bg-yellow-900/10">
                <h4 class="text-xs font-bold text-yellow-500 tracking-widest flex items-center gap-2">
                    <span class="material-symbols-outlined text-[14px]">warning</span>
                    ABANDONED WORK DETECTED
                </h4>
                <div class="flex flex-col gap-2">
                    {#each abandoned as item}
                        <div class="flex flex-col gap-1 border-l-2 border-yellow-500/50 pl-3">
                            <div class="flex items-center gap-2">
                                <span class="text-[10px] font-bold bg-yellow-500/20 text-yellow-500 px-1.5 py-0.5">{item.project || "UNKNOWN"}</span>
                                <span class="text-[10px] text-yellow-500/60">{item.time_ago || ""}</span>
                            </div>
                            <div class="text-xs text-yellow-500/90">{item.description}</div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        <div class="flex flex-col gap-6">
            {#each threads as thread}
                <div class="flex flex-col gap-3">
                    <div class="flex items-center gap-3 text-xs">
                        <span class="font-bold bg-primary/20 text-primary px-2 py-0.5 border border-primary/30">{thread.project}</span>
                        {#if thread.git_branch}
                            <span class="text-primary/70 flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">fork_right</span> {thread.git_branch}</span>
                        {/if}
                        <span class="text-[10px] text-primary/40 ml-auto">{thread.session_id}</span>
                    </div>

                    {#if thread.initial_goal || thread.hydrated_intent}
                        <div class="bg-black/40 border border-primary/20 p-3 text-xs leading-relaxed">
                            <strong class="text-primary/60">GOAL:</strong>
                            <span class="text-primary/90">{thread.hydrated_intent || thread.initial_goal}</span>
                        </div>
                    {/if}

                    <div class="flex flex-col gap-0 ml-2 border-l border-primary/20 pl-4 relative">
                        {#each thread.events as event}
                            <div class="relative py-3 group hover:bg-primary/5 -ml-4 pl-4 pr-2 transition-colors">
                                <!-- Marker -->
                                <div class="absolute left-[-4.5px] top-[18px] w-2 h-2 rounded-full bg-black border border-primary group-hover:bg-primary transition-colors"></div>

                                <div class="flex items-start gap-4">
                                    <div class="text-[10px] text-primary/50 pt-0.5 w-12 shrink-0">
                                        {formatTime(event.timestamp)}
                                    </div>
                                    <div class="flex flex-col gap-1 flex-1">
                                        <div class="text-xs text-primary/80 leading-relaxed">
                                            {event.narrative}
                                        </div>
                                        {#if event.task_id}
                                            <div class="text-[10px] text-primary/40 mt-1">
                                                ID: {event.task_id}
                                            </div>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    </div>
{/if}
