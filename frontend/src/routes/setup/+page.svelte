<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchAvailableRepos, registerRepos, pollJob } from '$lib/api';
	import type { GithubRepoPreview, JobStatus } from '$lib/api';

	let repos: GithubRepoPreview[] = $state([]);
	let loading = $state(true);
	let loadError: string | null = $state(null);
	let selected = $state(new Set<string>());
	let submitting = $state(false);
	let jobStatus: JobStatus | null = $state(null);
	let jobError: string | null = $state(null);
	let done = $state(false);

	onMount(async () => {
		try {
			repos = await fetchAvailableRepos();
		} catch (e: unknown) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	});

	// Group repos by owner
	let grouped = $derived(
		repos.reduce<Record<string, GithubRepoPreview[]>>((acc, r) => {
			const owner = r.full_name.split('/')[0];
			(acc[owner] ??= []).push(r);
			return acc;
		}, {})
	);

	function selectAll() {
		selected = new Set(repos.map((r) => r.full_name));
	}
	function deselectAll() {
		selected = new Set();
	}
	function toggle(fn: string) {
		const s = new Set(selected);
		s.has(fn) ? s.delete(fn) : s.add(fn);
		selected = s;
	}

	async function submit() {
		submitting = true;
		jobError = null;
		try {
			const job = await registerRepos([...selected]);
			jobStatus = job;
			const final = await pollJob(job.id, (s) => {
				jobStatus = s;
			});
			if (final.status === 'error') {
				jobError = final.error ?? 'Indexing failed';
			} else {
				done = true;
			}
		} catch (e: unknown) {
			jobError = e instanceof Error ? e.message : String(e);
		} finally {
			submitting = false;
		}
	}
</script>

<main>
	<h1>Set up repositories</h1>

	{#if loading}
		<p>Loading repositories...</p>
	{:else if loadError}
		<p class="error">{loadError}</p>
	{:else}
		<div class="controls">
			<button onclick={selectAll}>Select all</button>
			<button onclick={deselectAll}>Deselect all</button>
			<span>{selected.size} selected</span>
		</div>

		{#each Object.entries(grouped) as [owner, ownerRepos]}
			<section>
				<h2>{owner}</h2>
				{#each ownerRepos as repo}
					<label>
						<input
							type="checkbox"
							checked={selected.has(repo.full_name)}
							onchange={() => toggle(repo.full_name)}
						/>
						<strong>{repo.full_name.split('/')[1]}</strong>
						{#if repo.description}<span class="desc"> — {repo.description}</span>{/if}
						{#if repo.language}<span class="lang"> [{repo.language}]</span>{/if}
					</label>
				{/each}
			</section>
		{/each}

		<button onclick={submit} disabled={selected.size === 0 || submitting}>
			{submitting ? 'Indexing...' : 'Index selected repos'}
		</button>

		{#if jobStatus && !done}
			<p>Status: {jobStatus.status}</p>
		{/if}
		{#if jobError}
			<p class="error">{jobError}</p>
		{/if}
		{#if done}
			<p>Indexing complete. <a href="/">Go to chat</a></p>
		{/if}
	{/if}
</main>

<style>
	.error {
		color: red;
	}
	label {
		display: block;
		margin: 0.25rem 0;
	}
	.desc {
		color: #666;
	}
	.lang {
		color: #888;
		font-size: 0.85em;
	}
	section {
		margin-bottom: 1.5rem;
	}
</style>
