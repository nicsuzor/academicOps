import { writable } from 'svelte/store';

export const filters = writable({
    project: 'ALL',
    showActive: true,
    showBlocked: true,
    showCompleted: false,
    showOrphans: false,
    showDependencies: false,
    showReferences: false
});
