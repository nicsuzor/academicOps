import { writable, get } from 'svelte/store';

export interface SelectionState {
    activeNodeId: string | null;
    focusNodeId: string | null;  // non-null = ego network focus mode
    focusNeighborSet: Set<string> | null;
}

export const selection = writable<SelectionState>({
    activeNodeId: null,
    focusNodeId: null,
    focusNeighborSet: null
});

export function clearSelection() {
    selection.update(s => ({ ...s, activeNodeId: null }));
}

export function toggleSelection(nodeId: string) {
    selection.update(s => ({
        ...s,
        activeNodeId: s.activeNodeId === nodeId ? null : nodeId
    }));
}
