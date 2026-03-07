<script lang="ts">
	import favicon from "$lib/assets/favicon.svg";
	import "../app.css";
	import { onMount } from "svelte";

	let { children } = $props();

	let clock = $state("");

	onMount(() => {
		const updateClock = () => {
			const now = new Date();
			clock = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
		};
		const timer = setInterval(updateClock, 1000);
		updateClock();

		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<!-- Scanline Overlay -->
<div class="scanlines"></div>

<!-- Header -->
<header class="flex-none h-14 border-b border-primary/30 bg-surface-dark px-4 flex items-center justify-between z-10 relative">
	<div class="flex items-center gap-4">
		<div class="size-6 text-primary animate-pulse">
			<span class="material-symbols-outlined" style="font-size: 24px;">terminal</span>
		</div>
		<h1 class="text-lg font-bold tracking-widest text-primary text-glow">OPERATOR SYSTEM <span class="text-xs opacity-60 align-top">v1.0</span></h1>
	</div>

	<div class="flex items-center gap-6">
		<button class="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 hover:bg-primary/30 transition-colors hidden sm:flex cursor-pointer" onclick={() => document.documentElement.classList.toggle('theme-holographic')}>
			<span class="material-symbols-outlined text-sm">palette</span>
			<span class="text-xs font-mono font-bold tracking-wider text-primary">THEME</span>
		</button>
		<div class="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-none hidden sm:flex">
			<span class="material-symbols-outlined text-sm">wifi</span>
			<span class="text-xs font-mono font-bold tracking-wider">NET: SECURE</span>
		</div>
		<div class="flex items-center gap-2 px-3 py-1 bg-primary text-black border border-primary rounded-none font-bold">
			<span class="material-symbols-outlined text-sm animate-spin">sync</span>
			<span class="text-xs font-mono tracking-wider">SESSION: ACTIVE</span>
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

<style>
	/* CRT Scanline Effect */
	.scanlines {
		background: linear-gradient(
			to bottom,
			rgba(255,255,255,0),
			rgba(255,255,255,0) 50%,
			rgba(0,0,0,0.2) 50%,
			rgba(0,0,0,0.2)
		);
		background-size: 100% 4px;
		pointer-events: none;
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 50;
		opacity: 0.15;
	}

	.text-glow {
		text-shadow: 0 0 5px color-mix(in srgb, var(--color-primary) 50%, transparent);
	}

	:global(.grid-bg) {
		background-image:
			linear-gradient(color-mix(in srgb, var(--color-primary) 5%, transparent) 1px, transparent 1px),
			linear-gradient(90deg, color-mix(in srgb, var(--color-primary) 5%, transparent) 1px, transparent 1px);
		background-size: 24px 24px;
	}
</style>
