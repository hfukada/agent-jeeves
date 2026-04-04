<script lang="ts">
	import type { GithubRepoPreview, IndexJobResponse } from '$lib/api';
	import { listGithubRepos, createOrg, triggerIndex, getJob } from '$lib/api';

	let { oncomplete }: { oncomplete: (orgId: string) => void } = $props();

	let step = $state<1 | 2 | 3>(1);
	let org = $state('');
	let token = $state('');
	let repos = $state<GithubRepoPreview[]>([]);
	let selected = $state(new Set<string>());
	let orgId = $state('');
	let jobId = $state('');
	let jobStatus = $state<IndexJobResponse | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(false);

	let pollInterval: ReturnType<typeof setInterval> | null = null;

	function startPolling() {
		if (pollInterval !== null) return;
		pollInterval = setInterval(async () => {
			try {
				const status = await getJob(jobId);
				jobStatus = status;
				if (status.status === 'done') {
					stopPolling();
					oncomplete(orgId);
				} else if (status.status === 'error') {
					stopPolling();
					error = status.error ?? 'Indexing failed';
				}
			} catch (err) {
				error = err instanceof Error ? err.message : String(err);
			}
		}, 2000);
	}

	function stopPolling() {
		if (pollInterval !== null) {
			clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	$effect(() => {
		if (step === 3) {
			startPolling();
		}
		return () => {
			stopPolling();
		};
	});

	async function fetchRepos() {
		error = null;
		loading = true;
		try {
			const result = await listGithubRepos(org, token);
			repos = result;
			selected = new Set(result.map((r) => r.full_name));
			step = 2;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			loading = false;
		}
	}

	function toggleRepo(fullName: string, checked: boolean) {
		const next = new Set(selected);
		if (checked) {
			next.add(fullName);
		} else {
			next.delete(fullName);
		}
		selected = next;
	}

	function selectAll() {
		selected = new Set(repos.map((r) => r.full_name));
	}

	function deselectAll() {
		selected = new Set();
	}

	async function startIndexing() {
		error = null;
		loading = true;
		try {
			const createdOrg = await createOrg(org, token);
			orgId = createdOrg.id;
			const job = await triggerIndex(orgId, [...selected], token);
			jobId = job.job_id;
			step = 3;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			loading = false;
		}
	}
</script>

<div class="setup-flow">
	{#if step === 1}
		<div class="step">
			<h2>Connect GitHub</h2>
			<p>Enter a GitHub organization or username and a personal access token to discover repositories.</p>
			<form onsubmit={(e) => { e.preventDefault(); fetchRepos(); }}>
				<label>
					Organization / Username
					<input type="text" bind:value={org} placeholder="my-org" required />
				</label>
				<label>
					GitHub Token
					<input type="password" bind:value={token} placeholder="ghp_..." required />
				</label>
				{#if error}
					<p class="error">{error}</p>
				{/if}
				<button type="submit" disabled={loading}>
					{loading ? 'Fetching...' : 'Fetch repos'}
				</button>
			</form>
		</div>
	{:else if step === 2}
		<div class="step">
			<h2>Select repositories to index</h2>
			<div class="bulk-actions">
				<button type="button" onclick={selectAll}>Select all</button>
				<button type="button" onclick={deselectAll}>Deselect all</button>
			</div>
			<ul class="repo-list">
				{#each repos as repo}
					<li>
						<label>
							<input
								type="checkbox"
								checked={selected.has(repo.full_name)}
								onchange={(e) => toggleRepo(repo.full_name, (e.target as HTMLInputElement).checked)}
							/>
							<span class="repo-name">{repo.full_name}</span>
							{#if repo.private}
								<span class="badge">private</span>
							{/if}
							{#if repo.description}
								<span class="description">{repo.description}</span>
							{/if}
						</label>
					</li>
				{/each}
			</ul>
			{#if error}
				<p class="error">{error}</p>
			{/if}
			<button type="button" onclick={startIndexing} disabled={selected.size === 0 || loading}>
				{loading ? 'Starting...' : 'Index selected repos'}
			</button>
		</div>
	{:else}
		<div class="step">
			<h2>Indexing repositories</h2>
			{#if jobStatus}
				<p>Status: <strong>{jobStatus.status}</strong></p>
				<progress value={jobStatus.progress} max={100}></progress>
				<p>{jobStatus.progress}% complete</p>
			{:else}
				<p>Starting indexing job...</p>
			{/if}
			{#if error}
				<p class="error">{error}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.setup-flow {
		display: flex;
		justify-content: center;
		align-items: flex-start;
		padding: 3rem 1rem;
		min-height: 100%;
	}

	.step {
		width: 100%;
		max-width: 560px;
	}

	h2 {
		margin: 0 0 0.5rem;
		font-size: 1.4rem;
	}

	p {
		color: #94a3b8;
		margin: 0 0 1.25rem;
	}

	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		font-size: 0.875rem;
		color: #cbd5e1;
	}

	input[type='text'],
	input[type='password'] {
		padding: 0.5rem 0.75rem;
		border: 1px solid #334155;
		border-radius: 6px;
		background: #1e293b;
		color: #f1f5f9;
		font-size: 0.9rem;
	}

	input[type='text']:focus,
	input[type='password']:focus {
		outline: none;
		border-color: #6366f1;
	}

	button {
		padding: 0.55rem 1.1rem;
		border: none;
		border-radius: 6px;
		background: #6366f1;
		color: #fff;
		font-size: 0.9rem;
		cursor: pointer;
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	button:not(:disabled):hover {
		background: #4f46e5;
	}

	.bulk-actions {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.bulk-actions button {
		background: #334155;
		font-size: 0.8rem;
		padding: 0.35rem 0.75rem;
	}

	.bulk-actions button:hover {
		background: #475569;
	}

	.repo-list {
		list-style: none;
		padding: 0;
		margin: 0 0 1rem;
		max-height: 380px;
		overflow-y: auto;
		border: 1px solid #334155;
		border-radius: 6px;
	}

	.repo-list li {
		border-bottom: 1px solid #1e293b;
	}

	.repo-list li:last-child {
		border-bottom: none;
	}

	.repo-list label {
		flex-direction: row;
		align-items: baseline;
		gap: 0.5rem;
		padding: 0.6rem 0.75rem;
		cursor: pointer;
		flex-wrap: wrap;
	}

	.repo-list label:hover {
		background: #1e293b;
	}

	.repo-list input[type='checkbox'] {
		flex-shrink: 0;
	}

	.repo-name {
		font-size: 0.875rem;
		color: #f1f5f9;
	}

	.badge {
		font-size: 0.7rem;
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
		background: #334155;
		color: #94a3b8;
	}

	.description {
		font-size: 0.78rem;
		color: #64748b;
		flex-basis: 100%;
		padding-left: 1.4rem;
	}

	progress {
		width: 100%;
		height: 8px;
		border-radius: 4px;
		appearance: none;
	}

	.error {
		color: #f87171;
		font-size: 0.875rem;
		margin: 0.5rem 0;
	}
</style>
