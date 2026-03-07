import { writable } from 'svelte/store';

export const viewSettings = writable({
    mainTab: 'Dashboard', // 'Dashboard' or 'Task Graph'
    viewMode: 'Treemap',  // "Treemap", "Circle Pack", "Force Atlas 2", "SFDP", "Arc Diagram"
    topNLeaves: 80,
    liveSimulation: false,
    chargeStrength: 1.0,
    attractionStrength: 0.75,
    clusterPull: 0.4
});

export const getLayoutFromViewSettings = ($settings: any) => {
    switch ($settings.viewMode) {
        case 'Treemap':
            return 'treemap';
        case 'Circle Pack':
            return 'circle_pack';
        case 'Force Atlas 2':
        case 'SFDP':
            return 'force';
        case 'Arc Diagram':
            return 'arc';
        default:
            return 'force';
    }
}
