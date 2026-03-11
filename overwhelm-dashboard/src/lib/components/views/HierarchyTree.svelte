<script lang="ts">
    import { graphData } from "../../stores/graph";
    import { selection } from "../../stores/selection";

    export let taskId: string | null;

    $: task = taskId ? $graphData?.nodes.find(n => n.id === taskId) : undefined;

    // Find ancestors (up)
    $: ancestors = (() => {
        const list = [];
        let curr = task;
        const seen = new Set();
        while (curr && curr.parent && !seen.has(curr.parent)) {
            const parent = $graphData?.nodes.find(n => n.id === curr.parent);
            if (!parent) break;
            list.unshift(parent);
            seen.add(curr.parent);
            curr = parent;
        }
        return list;
    })();

    // Find children (down)
    $: children = $graphData?.nodes.filter(n => n.parent === taskId).sort((a, b) => (a.priority ?? 5) - (b.priority ?? 5)) || [];

    function select(id: string) {
        selection.update(s => ({ ...s, activeNodeId: id }));
    }
</script>

<div class="space-y-4 font-mono">
    <!-- Ancestors Path -->
    {#if ancestors.length > 0}
        <div class="space-y-1">
            <h4 class="text-[10px] font-bold text-primary/40 uppercase tracking-widest">Ancestry</h4>
            <div class="flex flex-col gap-1">
                {#each ancestors as ancestor, i}
                    <div class="flex items-center gap-2">
                        <div style="width: {i * 12}px" class="shrink-0 border-l border-primary/20 h-4 ml-2"></div>
                        <button
                            class="text-[10px] text-primary/60 hover:text-primary transition-colors truncate text-left"
                            onclick={() => select(ancestor.id)}
                        >
                            {ancestor.label}
                        </button>
                    </div>
                {/each}
            </div>
        </div>
    {/if}

    <!-- Current Node -->
    <div class="space-y-1">
        <h4 class="text-[10px] font-bold text-primary/40 uppercase tracking-widest">Active_Node</h4>
        <div class="flex items-center gap-2 p-2 bg-primary/10 border border-primary/30 rounded">
            <div style="width: {ancestors.length * 12}px" class="shrink-0"></div>
            <span class="text-xs font-bold text-primary truncate">{task?.label || taskId}</span>
        </div>
    </div>

    <!-- Children -->
    {#if children.length > 0}
        <div class="space-y-1">
            <h4 class="text-[10px] font-bold text-primary/40 uppercase tracking-widest">Descendants ({children.length})</h4>
            <div class="flex flex-col gap-1 max-h-64 overflow-y-auto custom-scrollbar pr-2">
                {#each children as child}
                    <div class="flex items-center gap-2">
                        <div style="width: {(ancestors.length + 1) * 12}px" class="shrink-0 border-l border-primary/20 h-4 ml-2"></div>
                        <button
                            class="text-[10px] text-primary/60 hover:text-primary transition-colors truncate text-left flex-1"
                            onclick={() => select(child.id)}
                        >
                            {child.label}
                        </button>
                        <span class="text-[8px] px-1 border border-primary/20 text-primary/40 rounded uppercase">{child.status}</span>
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
