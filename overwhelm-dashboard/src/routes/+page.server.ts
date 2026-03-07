import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const load = async () => {
    try {
        const { stdout, stderr } = await execAsync('uv run python3 src/lib/server/dump_dashboard_data.py', {
            cwd: '/Users/suzor/src/academicOps/overwhelm-dashboard',
            maxBuffer: 1024 * 1024 * 10
        });

        if (stderr && stderr.includes('Error')) {
            console.error("Python bridge stderr:", stderr);
        }

        const data = JSON.parse(stdout);
        return { dashboardData: data };
    } catch (e: any) {
        console.error("Failed to load dashboard data", e);
        return { dashboardData: null, error: e.message };
    }
};
