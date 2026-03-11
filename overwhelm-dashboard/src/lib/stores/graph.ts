import { writable } from 'svelte/store';
import type { PreparedGraph } from '../data/prepareGraphData';

export const graphData = writable<PreparedGraph | null>(null);
