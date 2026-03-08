/**
 * Graph visualization constants.
 *
 * Mirrored from lib/overwhelm/task_graph_d3.py — keep in sync.
 */

export const EDGE_FORCE = {
    parent: { strength: 1.0, distance: 40 },
    depends_on: { strength: 0.15, distance: 200 },
    ref: { strength: 0.02, distance: 300 },
} as const;

export const FORCE_CONFIG = {
    chargeDistanceMax: 280,
    chargeMult: 1.0,
    collisionPadding: 2,
    collisionStrength: 0.4,
    collisionIterations: 3,
    clusterStrength: 0.4,
    orphanRadius: 0.45,
    orphanStrength: 0.3,
    linkDistMult: 0.75,
    alphaDecay: 0.04,
    velocityDecay: 0.55,
    alphaMin: 0.002,
    warmupTicks: 80,
} as const;

export const TYPE_CHARGE: Record<string, number> = {
    goal: -500,
    project: -350,
    epic: -250,
    task: -150,
    action: -100,
    bug: -150,
    feature: -180,
    learn: -100,
    daily: -70,
    knowledge: -100,
    person: -100,
    context: -70,
    template: -60,
    note: -70,
};

export const TYPE_BASE_SCALE: Record<string, number> = {
    goal: 1.5,
    project: 1.25,
    epic: 1.1,
    task: 1.0,
    action: 0.85,
    bug: 1.0,
    feature: 1.05,
    learn: 0.85,
    daily: 0.7,
    knowledge: 0.8,
    person: 0.9,
    context: 0.75,
    template: 0.7,
    note: 0.8,
};

export const TYPE_SHAPE: Record<string, string> = {
    goal: "pill",
    project: "rounded",
    epic: "hexagon",
    task: "rect",
    action: "rect",
    bug: "rect",
    feature: "rounded",
    learn: "rect",
    daily: "rect",
    knowledge: "rect",
    person: "pill",
};

export const STATUS_FILLS: Record<string, string> = {
    done: "#dcfce7",
    completed: "#dcfce7",
    cancelled: "#f1f5f9",
    active: "#dbeafe",
    in_progress: "#c7d2fe",
    blocked: "#fee2e2",
    waiting: "#fef9c3",
    inbox: "#f1f5f9",
    todo: "#f1f5f9",
    review: "#f3e8ff",
    decomposing: "#e0f2fe",
    dormant: "#f1f5f9",
};

export const STATUS_TEXT: Record<string, string> = {
    done: "#166534",
    completed: "#166534",
    cancelled: "#94a3b8",
    active: "#1e3a5f",
    in_progress: "#312e81",
    blocked: "#991b1b",
    waiting: "#854d0e",
    inbox: "#475569",
    todo: "#475569",
    review: "#6b21a8",
    decomposing: "#0369a1",
    dormant: "#94a3b8",
};

export const TYPE_BADGE: Record<string, string> = {
    goal: "GOAL",
    project: "PROJECT",
    epic: "EPIC",
    task: "",
    action: "ACTION",
    bug: "BUG",
    feature: "FEATURE",
    learn: "LEARN",
};

export const ASSIGNEE_COLORS: Record<string, string> = {
    bot: "#17a2b8",
    claude: "#17a2b8",
    worker: "#fd7e14",
    nic: "#6f42c1",
};

export const ASSIGNEE_DEFAULT = "#6c757d";

export const PRIORITY_BORDERS: Record<number, string> = {
    0: "#dc3545",
    1: "#fd7e14",
    2: "#6c757d",
    3: "#adb5bd",
    4: "#dee2e6",
};

export const INCOMPLETE_STATUSES = new Set([
    "inbox",
    "active",
    "in_progress",
    "blocked",
    "waiting",
    "todo",
    "pending",
]);

export const MUTED_FILL = "#e8eaed";
export const MUTED_TEXT = "#9ca3af";
