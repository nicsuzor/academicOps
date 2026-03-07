<script lang="ts">
    export let synthesis: any;
    export let dailyStory: any;

    $: hasSynthesis = synthesis && Object.keys(synthesis).length > 0;
    $: storyParagraphs = dailyStory?.story || synthesis?.daily_story || [];
    $: hasStory = storyParagraphs && storyParagraphs.length > 0;
</script>

{#if hasSynthesis || hasStory}
    <div class="glass-surface synthesis-panel">
        <div class="synthesis-header">
            <h3 class="synthesis-title">SYNTHESIS & INSIGHTS</h3>
            {#if synthesis?._age_minutes !== undefined}
                <span class="synthesis-age"
                    >{Math.round(synthesis._age_minutes)}m ago</span
                >
            {/if}
        </div>

        {#if hasStory}
            <div class="synthesis-narrative">
                <h4 class="synthesis-narrative-title">Daily Story</h4>
                <div class="synthesis-narrative-content">
                    {#each storyParagraphs as paragraph}
                        <p>{paragraph}</p>
                    {/each}
                </div>
            </div>
        {/if}

        {#if hasSynthesis}
            <div class="synthesis-grid">
                {#if synthesis.alignment}
                    <div
                        class="synthesis-card alignment {synthesis.alignment
                            .status || ''}"
                    >
                        <div class="synthesis-card-title">Alignment</div>
                        <div class="synthesis-card-content">
                            {synthesis.alignment.assessment ||
                                synthesis.alignment}
                        </div>
                    </div>
                {/if}

                {#if synthesis.recent_context}
                    <div class="synthesis-card context">
                        <div class="synthesis-card-title">Current Context</div>
                        <div class="synthesis-card-content">
                            {synthesis.recent_context}
                        </div>
                    </div>
                {/if}

                {#if synthesis.blockers}
                    <div class="synthesis-card waiting">
                        <div class="synthesis-card-title">Blockers</div>
                        <div class="synthesis-card-content">
                            <ul>
                                {#each Array.isArray(synthesis.blockers) ? synthesis.blockers : [synthesis.blockers] as blocker}
                                    <li>{blocker}</li>
                                {/each}
                            </ul>
                        </div>
                    </div>
                {/if}
            </div>
        {/if}
    </div>
{/if}

<style>
    .synthesis-panel {
        padding: 32px;
        height: 100%;
        box-sizing: border-box;
    }
    .synthesis-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--border-subtle);
        padding-bottom: 12px;
    }

    .synthesis-title {
        font-size: 15px;
        font-weight: 800;
        color: var(--text-primary);
        margin: 0;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .synthesis-age {
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 500;
    }

    .synthesis-narrative {
        background: rgba(99, 102, 241, 0.05);
        border-left: 3px solid var(--accent-primary);
        padding: 20px;
        margin-bottom: 24px;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
    }

    .synthesis-narrative-title {
        color: var(--accent-primary);
        font-weight: 700;
        font-size: 12px;
        margin: 0 0 12px 0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .synthesis-narrative-content {
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.7;
    }

    .synthesis-narrative-content p {
        margin: 0 0 12px 0;
    }
    .synthesis-narrative-content p:last-child {
        margin-bottom: 0;
    }

    .synthesis-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
    }

    .synthesis-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 20px;
        transition:
            transform var(--transition-fast),
            box-shadow var(--transition-fast);
    }

    .synthesis-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-sm);
    }

    .synthesis-card-title {
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .synthesis-card-content {
        font-size: 13px;
        line-height: 1.6;
        color: var(--text-secondary);
        font-weight: 500;
    }

    .synthesis-card-content ul {
        margin: 0;
        padding-left: 20px;
    }

    .synthesis-card-content li {
        margin-bottom: 6px;
    }

    .synthesis-card.alignment .synthesis-card-title {
        color: var(--accent-warning);
    }
    .synthesis-card.alignment.on_track .synthesis-card-title {
        color: var(--accent-success);
    }
    .synthesis-card.alignment.blocked .synthesis-card-title {
        color: var(--accent-danger);
    }

    .synthesis-card.context .synthesis-card-title {
        color: #38bdf8; /* Light blue */
    }
    .synthesis-card.waiting .synthesis-card-title {
        color: var(--accent-danger);
    }
</style>
