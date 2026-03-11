<script lang="ts">
    export let synthesis: any;
    export let dailyStory: any;

    $: hasSynthesis = synthesis && Object.keys(synthesis).length > 0;
    $: rawStoryParagraphs = dailyStory?.story || synthesis?.daily_story || [];
    $: storyParagraphs = rawStoryParagraphs.reduce((acc, curr) => {
        const existing = acc.find(item => item.text === curr);
        if (existing) {
            existing.count++;
        } else {
            acc.push({ text: curr, count: 1 });
        }
        return acc;
    }, []).map(item => item.count > 1 ? `[${item.count}x] ${item.text}` : item.text);
    $: hasStory = storyParagraphs && storyParagraphs.length > 0;
</script>

{#if hasSynthesis || hasStory}
    <div class="flex flex-col gap-4 font-mono">
        <div class="flex justify-between items-baseline border-b border-primary/30 pb-2 mb-2">
            <h3 class="text-xs font-bold tracking-[0.2em] text-primary/80">SYNTHESIS & INSIGHTS</h3>
            {#if synthesis?._age_minutes !== undefined}
                <span class="text-[10px] text-primary/60"
                    >{Math.round(synthesis._age_minutes)}m ago</span
                >
            {/if}
        </div>

        {#if hasStory}
            <div class="bg-primary/5 border-l-2 border-primary p-4 mb-4">
                <h4 class="text-[10px] font-bold tracking-widest text-primary mb-3">DAILY STORY</h4>
                <div class="text-sm text-primary/80 space-y-3 leading-relaxed">
                    {#each storyParagraphs as paragraph}
                        <p>{paragraph}</p>
                    {/each}
                </div>
            </div>
        {/if}

        {#if hasSynthesis}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {#if synthesis.alignment}
                    <div class="bg-black/50 border border-primary/30 p-4 hover:border-primary transition-colors">
                        <div class="text-[10px] font-bold tracking-widest text-primary/60 mb-2">ALIGNMENT</div>
                        <div class="text-sm text-primary/90">
                            {typeof synthesis.alignment === 'string' ? synthesis.alignment : (synthesis.alignment.assessment || JSON.stringify(synthesis.alignment))}
                        </div>
                    </div>
                {/if}

                {#if synthesis.recent_context}
                    <div class="bg-black/50 border border-primary/30 p-4 hover:border-primary transition-colors">
                        <div class="text-[10px] font-bold tracking-widest text-primary/60 mb-2">CURRENT CONTEXT</div>
                        <div class="text-sm text-primary/90">
                            {synthesis.recent_context}
                        </div>
                    </div>
                {/if}

                {#if synthesis.blockers}
                    <div class="bg-red-900/10 border border-red-500/30 p-4 hover:border-red-500 transition-colors col-span-1 md:col-span-2">
                        <div class="text-[10px] font-bold tracking-widest text-red-500/80 mb-2">BLOCKERS</div>
                        <ul class="list-disc list-inside text-sm text-red-400 space-y-1 ml-4">
                            {#each Array.isArray(synthesis.blockers) ? synthesis.blockers : [synthesis.blockers] as blocker}
                                <li>{blocker}</li>
                            {/each}
                        </ul>
                    </div>
                {/if}
            </div>
        {/if}
    </div>
{/if}
