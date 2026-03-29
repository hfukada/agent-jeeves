<script lang="ts">
	let { children } = $props();
</script>

<svelte:head>
	<title>Agent Jeeves - Code Knowledge Base</title>
</svelte:head>

<div class="app">
	<header>
		<h1>Agent Jeeves</h1>
		<p>Code knowledge base for multi-repository organizations</p>
	</header>
	<main>
		{@render children()}
	</main>
</div>

<style>
	:global(body) {
		margin: 0;
		font-family:
			-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
			sans-serif;
		background: #f8fafc;
		color: #1e293b;
	}

	.app {
		max-width: 900px;
		margin: 0 auto;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	header {
		padding: 1.5rem 1rem 1rem;
		text-align: center;
		border-bottom: 1px solid #e2e8f0;
		background: #fff;
	}

	header h1 {
		margin: 0;
		font-size: 1.5rem;
		color: #0f172a;
	}

	header p {
		margin: 0.25rem 0 0;
		font-size: 0.85rem;
		color: #94a3b8;
	}

	main {
		flex: 1;
		display: flex;
		flex-direction: column;
	}
</style>
