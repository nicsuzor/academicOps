import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const AOPS_BRAIN = env.AOPS_BRAIN || '';

/** GET /api/task?path=tasks/some-task.md — fetch task markdown body */
export const GET: RequestHandler = async ({ url }) => {
    if (!AOPS_BRAIN) {
        return json({ error: 'AOPS_BRAIN environment variable is not set' }, { status: 503 });
    }

    const path = url.searchParams.get('path');
    if (!path) {
        return json({ error: 'Missing path parameter' }, { status: 400 });
    }

    // Sanitize: only allow relative paths within AOPS_BRAIN
    if (path.includes('..') || path.startsWith('/')) {
        return json({ error: 'Invalid path' }, { status: 400 });
    }

    const filepath = join(AOPS_BRAIN, path);

    try {
        const text = await readFile(filepath, 'utf-8');

        // Extract body (strip frontmatter)
        let body = text;
        if (text.startsWith('---')) {
            const end = text.indexOf('\n---', 3);
            if (end !== -1) {
                body = text.substring(end + 4).trim();
            }
        }

        return json({ body });
    } catch (e: any) {
        return json({ error: `Task file not found: ${path}` }, { status: 404 });
    }
};
