import { readFile, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { env } from '$env/dynamic/private';

const ACA_DATA = env.ACA_DATA || '/opt/nic/brain';

async function readJson(path: string): Promise<any | null> {
    try {
        const text = await readFile(path, 'utf-8');
        return JSON.parse(text);
    } catch {
        return null;
    }
}

async function loadSynthesis(): Promise<any | null> {
    const path = join(ACA_DATA, 'dashboard', 'synthesis.json');
    const data = await readJson(path);
    if (!data) return null;

    try {
        const st = await stat(path);
        data._age_minutes = (Date.now() - st.mtimeMs) / 60000;
    } catch { /* ignore */ }

    return data;
}

async function findActiveSessions(hours = 4): Promise<any[]> {
    const claudeProjects = join(env.HOME || '/home/debian', '.claude', 'projects');
    const cutoff = Date.now() - hours * 3600 * 1000;
    const results: any[] = [];

    let projectDirs: string[];
    try {
        projectDirs = await readdir(claudeProjects);
    } catch {
        return results;
    }

    for (const projName of projectDirs) {
        if (projName.includes('-tmp') || projName.includes('-var-folders') || projName.endsWith('-hooks')) continue;

        const projPath = join(claudeProjects, projName);
        let sessionDirs: string[];
        try {
            sessionDirs = await readdir(projPath);
        } catch {
            continue;
        }

        for (const sessName of sessionDirs) {
            if (!/^\d/.test(sessName)) continue;
            const stateFile = join(projPath, sessName, 'session-state.json');
            let st;
            try {
                st = await stat(stateFile);
            } catch {
                continue;
            }
            if (st.mtimeMs < cutoff) continue;

            const stateData = await readJson(stateFile);
            if (!stateData) continue;

            const insights = stateData.insights || {};
            const project = insights.project || stateData.project || formatProjectName(projName);
            const minutesAgo = (Date.now() - st.mtimeMs) / 60000;

            results.push({
                session_id: stateData.session_id || sessName.split('-').pop(),
                project,
                description: insights.summary || stateData.summary || stateData.current_task || '',
                goal: insights.goal || '',
                started_at: new Date(st.mtimeMs - (stateData.duration_ms || 0)).toISOString(),
                time_display: minutesAgo < 60 ? `${Math.round(minutesAgo)}m ago` : `${Math.round(minutesAgo / 60)}h ago`,
                now_task: insights.current_task || stateData.current_task || '',
                next_task: insights.next_task || '',
                progress_done: insights.progress_done ?? 0,
                progress_total: insights.progress_total ?? 0,
                outcome_text: insights.outcome || '',
                is_active: minutesAgo < 10,
                last_modified: st.mtimeMs,
            });
        }
    }

    results.sort((a, b) => b.last_modified - a.last_modified);
    return results;
}

function formatProjectName(folder: string): string {
    const parts = folder.replace(/^-/, '').split('-');
    const skip = new Set(['home', 'Users', 'debian', 'nic', 'src', 'opt', '_aops', '']);
    const meaningful = parts.filter(p => !skip.has(p) && !/^[a-f0-9]{8,}$/.test(p));
    return meaningful.pop() || folder;
}

export const load = async () => {
    const [synthesis, sessions] = await Promise.all([
        loadSynthesis(),
        findActiveSessions(24),
    ]);

    const activeSessions = sessions.filter(s => s.is_active);
    const recentActive = sessions.filter(s => {
        const mins = (Date.now() - s.last_modified) / 60000;
        return mins < 240; // last 4h
    });
    const paused = sessions.filter(s => {
        const mins = (Date.now() - s.last_modified) / 60000;
        return mins >= 240 && mins < 1440; // 4-24h
    });

    // Build project-level data from synthesis
    const projectProjects: string[] = synthesis?.sessions?.by_project
        ? Object.keys(synthesis.sessions.by_project)
        : [];

    const projectData: any = { meta: {}, tasks: {}, accomplishments: {}, sessions: {} };
    if (synthesis) {
        for (const proj of projectProjects) {
            projectData.meta[proj] = {};
            projectData.tasks[proj] = [];
            projectData.sessions[proj] = sessions.filter(s => s.project === proj);
            projectData.accomplishments[proj] = (synthesis.accomplishments?.items || [])
                .filter((a: any) => a.project === proj)
                .map((a: any) => ({ description: a.text }));
        }
    }

    return {
        dashboardData: {
            active_agents: activeSessions.map(s => ({
                project: s.project,
                description: s.description,
                started_at: s.started_at,
            })),
            needs_you: [],
            left_off: {
                active: recentActive,
                paused,
            },
            synthesis: synthesis ? {
                alignment: synthesis.alignment,
                recent_context: synthesis.context?.recent_threads?.join(', ') || '',
                blockers: synthesis.waiting_on?.length ? synthesis.waiting_on : null,
                _age_minutes: synthesis._age_minutes,
            } : null,
            daily_story: synthesis?.narrative ? { story: synthesis.narrative } : null,
            project_projects: projectProjects,
            project_data: projectData,
            path: null,
        },
    };
};
