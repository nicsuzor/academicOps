<script lang="ts">
	import favicon from "$lib/assets/favicon.svg";
	import "../app.css";
	import { onMount } from "svelte";
	import { viewSettings } from "$lib/stores/viewSettings";

	let { children } = $props();

	let clock = $state("");

	onMount(() => {
		const updateClock = () => {
			const now = new Date();
			clock = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
		};
		const timer = setInterval(updateClock, 1000);
		updateClock();

		// Sync initial theme state to DOM
		if ($viewSettings.theme === 'holographic') {
			document.documentElement.classList.add('theme-holographic');
		}

		return () => clearInterval(timer);
	});

	function toggleTheme() {
		viewSettings.update(s => {
			s.theme = s.theme === 'operator' ? 'holographic' : 'operator';
			if (s.theme === 'holographic') {
				document.documentElement.classList.add('theme-holographic');
			} else {
				document.documentElement.classList.remove('theme-holographic');
			}
			return s;
		});
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<!-- Conditional Layout Wrapping -->
{#if $viewSettings.theme === 'operator'}
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
			<button class="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 hover:bg-primary/30 transition-colors hidden sm:flex cursor-pointer" onclick={toggleTheme}>
				<span class="material-symbols-outlined text-sm">palette</span>
				<span class="text-xs font-mono font-bold tracking-wider text-primary">{$viewSettings.theme.toUpperCase()}</span>
			</button>
			<div class="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-none hidden sm:flex">
				<span class="material-symbols-outlined text-sm">wifi</span>
				<span class="text-xs font-mono font-bold tracking-wider">NET: SECURE</span>
			</div>
			<div class="flex items-center gap-2 text-primary font-mono">
				<span class="material-symbols-outlined text-sm">schedule</span>
				<span class="text-sm">{clock}</span>
			</div>
		</div>
	</header>

	<!-- Main Content Area Wrapper -->
	<main class="flex-1 grid grid-cols-12 gap-0 overflow-hidden relative z-0 h-[calc(100vh-3.5rem)]">
		{@render children()}
	</main>
{:else}
	<!-- Holographic Layout -->
	<div class="relative flex h-screen w-full flex-col void-bg overflow-hidden text-slate-100">
		<!-- Floating Nav -->
		<header class="flex-none z-50 flex items-center justify-between px-6 py-4 glass-panel border-b border-primary/10">
			<div class="flex items-center gap-3">
				<div class="bg-primary p-1 rounded">
					<span class="material-symbols-outlined text-background text-xl font-bold">deployed_code</span>
				</div>
				<h2 class="text-slate-100 text-xl font-bold tracking-tight uppercase">Holographic</h2>
			</div>
			<div class="flex items-center gap-6">
				<button class="flex items-center gap-2 px-4 py-2 glass-card hover:bg-primary/20 transition-colors hidden sm:flex cursor-pointer rounded-lg" onclick={toggleTheme}>
					<span class="material-symbols-outlined text-sm text-primary">palette</span>
					<span class="text-xs font-mono font-bold tracking-wider text-primary">{$viewSettings.theme.toUpperCase()}</span>
				</button>
			</div>
		</header>

		<!-- Main Content Area Wrapper -->
		<main class="flex-1 relative z-0 overflow-hidden">
			{@render children()}
		</main>

		<!-- Void Graph Decorative Layer (Absolute Background) -->
		<div class="absolute inset-0 -z-10 pointer-events-none opacity-20 overflow-hidden">
			<svg class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[150%] h-[150%] blur-3xl" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
				<path d="M44.7,-76.4C58.8,-69.2,71.8,-59.1,79.6,-46.2C87.4,-33.3,90,-16.6,89.1,-0.5C88.2,15.6,83.8,31.2,75.4,44.1C67,57,54.6,67.3,40.5,74.5C26.4,81.7,10.7,85.8,-4,92.7C-18.7,99.6,-32.4,109.3,-44.6,106.3C-56.8,103.3,-67.5,87.6,-74.3,72.2C-81.1,56.8,-84.1,41.7,-87.3,26.5C-90.5,11.3,-94,-3.9,-91.3,-18.3C-88.6,-32.7,-79.8,-46.3,-68.2,-55.5C-56.6,-64.7,-42.2,-69.5,-29.1,-77.2C-16.1,-84.9,-4.3,-95.5,8.8,-110.7C21.9,-125.9,43.8,-145.7,44.7,-76.4Z" fill="var(--color-primary)" transform="translate(100 100)"></path>
			</svg>
			<div class="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background"></div>
		</div>
	</div>
{/if}
