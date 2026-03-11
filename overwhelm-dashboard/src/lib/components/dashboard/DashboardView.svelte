<script lang="ts">
    export let data: any;

    import ActiveSessions from "./ActiveSessions.svelte";
    import WhereYouLeftOff from "./WhereYouLeftOff.svelte";
    import SynthesisPanel from "./SynthesisPanel.svelte";
    import PathTimeline from "./PathTimeline.svelte";
    import ProjectDashboard from "./ProjectDashboard.svelte";
    import QuickCapture from "./QuickCapture.svelte";
</script>

<div class="h-full p-8 font-mono text-primary flex flex-col gap-6">
    <div class="border border-primary/30 bg-surface p-4">
        <ActiveSessions
            sessions={data?.dashboardData?.active_agents || []}
            needsYou={data?.dashboardData?.needs_you || []}
        />
    </div>

    <div class="grid grid-cols-12 gap-6 flex-1 min-h-0">
        <div class="col-span-8 flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
            {#if data?.dashboardData?.left_off && (data.dashboardData.left_off.active?.length > 0 || data.dashboardData.left_off.paused?.length > 0)}
            <div class="border border-primary/30 bg-surface p-4">
                <WhereYouLeftOff leftOff={data?.dashboardData?.left_off} />
            </div>
            {/if}

            <div class="border border-primary/30 bg-surface p-4">
                <ProjectDashboard
                    projectProjects={data?.dashboardData?.project_projects || []}
                    projectData={data?.dashboardData?.project_data || {}}
                />
            </div>

            {#if data?.dashboardData?.path}
                <div class="border border-primary/30 bg-surface p-4">
                    <PathTimeline path={data?.dashboardData?.path} />
                </div>
            {/if}
        </div>

        <div class="col-span-4 flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2 bg-black/40 p-4 border border-primary/20 rounded-xl">
            <div class="border border-primary/30 bg-surface p-4 shadow-lg">
                <QuickCapture />
            </div>

            <div class="border border-primary/30 bg-surface p-4 shadow-lg">
                <SynthesisPanel
                    synthesis={data?.dashboardData?.synthesis}
                    dailyStory={data?.dashboardData?.daily_story}
                />
            </div>
        </div>
    </div>
</div>
