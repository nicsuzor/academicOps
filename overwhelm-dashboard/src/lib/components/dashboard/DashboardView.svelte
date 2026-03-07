<script lang="ts">
    export let data: any;

    import ActiveSessions from "./ActiveSessions.svelte";
    import WhereYouLeftOff from "./WhereYouLeftOff.svelte";
    import SynthesisPanel from "./SynthesisPanel.svelte";
    import PathTimeline from "./PathTimeline.svelte";
    import ProjectDashboard from "./ProjectDashboard.svelte";
    import QuickCapture from "./QuickCapture.svelte";
</script>

<div class="dashboard-container">
    <div class="top-row">
        <ActiveSessions
            sessions={data?.dashboardData?.active_agents || []}
            needsYou={data?.dashboardData?.needs_you || []}
        />
    </div>

    <div class="main-columns">
        <div class="left-col">
            <WhereYouLeftOff leftOff={data?.dashboardData?.left_off} />
            <ProjectDashboard
                projectProjects={data?.dashboardData?.project_projects || []}
                projectData={data?.dashboardData?.project_data || {}}
            />
            {#if data?.dashboardData?.path}
                <PathTimeline path={data?.dashboardData?.path} />
            {/if}
        </div>
        <div class="right-col">
            <QuickCapture />
            <SynthesisPanel
                synthesis={data?.dashboardData?.synthesis}
                dailyStory={data?.dashboardData?.daily_story}
            />
        </div>
    </div>
</div>

<style>
    .dashboard-container {
        padding: 32px 40px;
        color: var(--text-primary);
        overflow-y: auto;
        height: 100vh;
        box-sizing: border-box;
    }

    .top-row {
        margin-bottom: 24px;
    }

    .main-columns {
        display: flex;
        gap: 24px;
    }

    .left-col {
        flex: 3;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }

    .right-col {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }
</style>
