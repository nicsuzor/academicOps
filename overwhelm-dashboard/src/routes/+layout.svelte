<script lang="ts">
	import favicon from "$lib/assets/favicon.svg";
	import "../app.css";
	import { viewSettings } from "$lib/stores/viewSettings";

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<!-- Scanline Overlay -->
<div class="scanlines"></div>

<!-- Header -->
<header class="flex-none h-14 border-b border-primary/30 bg-surface px-4 flex items-center justify-between z-10 relative">
	<div class="flex items-center gap-8">
		<div class="flex items-center gap-4">
			<div class="size-6 text-primary animate-pulse">
				<span class="material-symbols-outlined" style="font-size: 24px;">terminal</span>
			</div>
			<h1 class="text-lg font-bold tracking-widest text-primary text-glow">OPERATOR SYSTEM <span class="text-xs opacity-60 align-top">v1.0</span></h1>
		</div>

		<!-- Navigation Links -->
		<nav class="hidden lg:flex items-center gap-6">
			<button
				class="text-xs font-bold uppercase transition-colors border-b-2 {$viewSettings.mainTab === 'Dashboard' ? 'border-primary text-primary' : 'border-transparent text-primary/60 hover:text-primary hover:border-primary/50'}"
				onclick={() => $viewSettings.mainTab = 'Dashboard'}
			>
				DASHBOARD
			</button>
			<button
				class="text-xs font-bold uppercase transition-colors border-b-2 {$viewSettings.mainTab === 'Task Graph' ? 'border-primary text-primary' : 'border-transparent text-primary/60 hover:text-primary hover:border-primary/50'}"
				onclick={() => $viewSettings.mainTab = 'Task Graph'}
			>
				TASK GRAPH
			</button>
			<button
				class="text-xs font-bold uppercase transition-colors border-b-2 {$viewSettings.mainTab === 'Threaded Tasks' ? 'border-primary text-primary' : 'border-transparent text-primary/60 hover:text-primary hover:border-primary/50'}"
				onclick={() => $viewSettings.mainTab = 'Threaded Tasks'}
			>
				THREADED TASKS
			</button>
		</nav>
	</div>

	<div class="flex items-center gap-6">
		<button class="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 hover:bg-primary/30 transition-colors hidden sm:flex cursor-pointer" onclick={() => $viewSettings.showSidebar = !$viewSettings.showSidebar}>
			<span class="material-symbols-outlined text-sm">{$viewSettings.showSidebar ? 'right_panel_close' : 'right_panel_open'}</span>
			<span class="text-xs font-mono font-bold tracking-wider text-primary">SIDEBAR</span>
		</button>
	</div>
</header>

<!-- Main Content Area Wrapper -->
<main class="flex-1 grid grid-cols-12 gap-0 overflow-hidden relative z-0 h-[calc(100vh-3.5rem)]">
	{@render children()}
</main>
