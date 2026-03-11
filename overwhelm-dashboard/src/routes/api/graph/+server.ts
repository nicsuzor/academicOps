import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const AOPS_SESSIONS = env.AOPS_SESSIONS;

/** GET /api/graph?layout=fa2 — serve graph JSON from $AOPS_SESSIONS */
export const GET: RequestHandler = async ({ url }) => {
    if (!AOPS_SESSIONS) {
        return json({ error: 'AOPS_SESSIONS environment variable is not set' }, { status: 503 });
    }

    const rawLayout = url.searchParams.get('layout') || 'fa2';
    // Sanitize: only allow alphanumeric, hyphens, underscores to prevent path traversal
    const layout = rawLayout.replace(/[^a-zA-Z0-9_-]/g, '');

    // List available layouts
    if (layout === '_list') {
        try {
            const files = await readdir(AOPS_SESSIONS);
            const layouts = files
                .filter(f => /^graph-[\w-]+\.json$/.test(f) && !f.includes('-focus'))
                .map(f => f.replace(/^graph-/, '').replace(/\.json$/, ''))
                .sort();
            return json({ layouts });
        } catch {
            return json({ layouts: [] });
        }
    }

    const filename = `graph-${layout}.json`;
    const filepath = join(AOPS_SESSIONS, filename);

    try {
        const text = await readFile(filepath, 'utf-8');
        return new Response(text, {
            headers: { 'Content-Type': 'application/json' },
        });
    } catch {
        return json({ error: `Layout "${layout}" not found` }, { status: 404 });
    }
};
