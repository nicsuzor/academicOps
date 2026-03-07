<script lang="ts">
    export let leftOff: any;

    $: active = leftOff?.active || [];
    $: paused = leftOff?.paused || [];
</script>

<div class="flex flex-col gap-4 font-mono">
    <h3 class="text-xs font-bold tracking-[0.2em] text-primary/80 border-b border-primary/30 pb-2 mb-2">WHERE YOU LEFT OFF</h3>

    {#if active.length === 0 && paused.length === 0}
        <div class="text-primary/50 text-xs italic">No recent sessions found.</div>
    {/if}

    {#if active.length > 0}
        <div class="mb-4">
            <h4 class="text-sm text-primary font-bold mb-3 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Active (last 4h)
            </h4>
            <div class="flex flex-col gap-3">
                {#each active as session}
                    <div class="bg-black border border-primary/30 p-4 relative group hover:border-primary transition-colors">
                        <div class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-xs font-bold bg-primary/10 text-primary px-2 py-0.5 border border-primary/20">{session.project}</span>
                            <span class="text-[10px] text-primary/60">{session.time_display}</span>
                        </div>
                        <div class="text-sm text-primary/90 mb-3">
                            {session.goal || session.description}
                        </div>

                        {#if session.now_task}
                            <div class="flex items-start gap-2 text-xs text-primary bg-primary/5 p-2 border-l border-primary/50 mb-2">
                                <span class="material-symbols-outlined text-[14px] animate-pulse">play_arrow</span>
                                <span>{session.now_task}</span>
                            </div>
                        {/if}

                        {#if session.next_task}
                            <div class="flex items-start gap-2 text-xs text-primary/60 p-2 mb-2">
                                <span class="material-symbols-outlined text-[14px]">hourglass_empty</span>
                                <span>{session.next_task}</span>
                            </div>
                        {/if}

                        {#if session.progress_total > 0}
                            <div class="flex items-center gap-3 mt-3">
                                <div class="flex-1 h-1.5 bg-black border border-primary/30 overflow-hidden">
                                    <div
                                        class="h-full bg-primary"
                                        style="width: {(session.progress_done / session.progress_total) * 100}%"
                                    ></div>
                                </div>
                                <span class="text-[10px] text-primary/70 font-bold"
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
        <div>
            <h4 class="text-sm text-primary/60 font-bold mb-3 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-yellow-500"></span> Paused (4-24h)
            </h4>
            <div class="flex flex-col gap-3">
                {#each paused as session}
                    <div class="bg-black/50 border border-primary/20 p-4 opacity-80 hover:opacity-100 transition-opacity">
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-xs font-bold text-primary/70">{session.project}</span>
                            <span class="text-[10px] text-primary/50">{session.time_display}</span>
                        </div>
                        <div class="text-sm text-primary/80 mb-2">
                            {session.goal || session.description}
                        </div>
                        {#if session.outcome_text}
                            <div class="text-xs text-primary/60 italic border-l border-primary/30 pl-2">
                                {session.outcome_text}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
