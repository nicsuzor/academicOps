import { writable } from 'svelte/store';

export const filters = writable({
    project: 'ALL',
    showActive: true,
    showBlocked: true,
    showCompleted: false, // Streamlit defaults to false
    showOrphans: false,   // Streamlit defaults to false for SFDP
    showDependencies: false,
    showReferences: false
});
