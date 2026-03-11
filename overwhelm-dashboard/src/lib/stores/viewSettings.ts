import { writable } from 'svelte/store';

export const viewSettings = writable({
    showSidebar: false, // controls sidebar visibility
    mainTab: 'Dashboard', // 'Dashboard' or 'Task Graph'
    viewMode: 'Treemap',  // "Treemap", "Circle Pack", "Force Atlas 2", "SFDP", "Arc Diagram"
    topNLeaves: 80,
    liveSimulation: false,
    chargeStrength: 1.0,
    linkDistance: 1.0,
    collisionRadius: 1.0,
    gravity: 0.05,
    alphaDecay: 0.04,
    velocityDecay: 0.55,
    circleRollupThreshold: 15,
    arcVerticalSpacing: 1.0
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

/** Map view mode to the graph JSON filename key in $AOPS_SESSIONS */
export const getGraphLayoutKey = ($settings: any): string => {
    switch ($settings.viewMode) {
        case 'Treemap':
            return 'tree';
        case 'Circle Pack':
            return 'circle';
        case 'Force Atlas 2':
            return 'fa2';
        case 'SFDP':
            return 'sfdp';
        case 'Arc Diagram':
            return 'arc';
        default:
            return 'fa2';
    }
}
