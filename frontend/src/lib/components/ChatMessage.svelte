<script lang="ts">
	import type { QueryResponse } from '$lib/api';

	let { message }: { message: { question: string; response: QueryResponse | null } } = $props();
</script>

<div class="message-group">
	<div class="question">
		<span class="label">Q</span>
		<p>{message.question}</p>
	</div>

	{#if message.response}
		<div class="answer" class:error={message.response.status === 'error'}>
			<span class="label">A</span>
			<div class="content">
				{#if message.response.status === 'pending' || message.response.status === 'processing'}
					<p class="loading">Searching...</p>
				{:else if message.response.answer}
					<pre>{message.response.answer}</pre>
					{#if message.response.sources.length > 0}
						<div class="sources">
							<strong>Sources:</strong>
							{#each message.response.sources as source}
								<div class="source">
									<span class="repo">{source.repo}</span>
									<span class="score">({source.score})</span>
									<span class="files">{source.files.join(', ')}</span>
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{:else}
		<div class="answer">
			<span class="label">A</span>
			<p class="loading">Searching...</p>
		</div>
	{/if}
</div>

<style>
	.message-group {
		margin-bottom: 1.5rem;
	}

	.question,
	.answer {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
	}

	.question {
		background: #f1f5f9;
		border-radius: 8px;
		margin-bottom: 0.5rem;
	}

	.answer {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
	}

	.answer.error {
		border-color: #fca5a5;
		background: #fef2f2;
	}

	.label {
		font-weight: 700;
		font-size: 0.8rem;
		color: #64748b;
		min-width: 1.5rem;
		text-align: center;
		padding-top: 0.15rem;
	}

	.content {
		flex: 1;
		min-width: 0;
	}

	pre {
		white-space: pre-wrap;
		word-break: break-word;
		font-size: 0.9rem;
		line-height: 1.6;
		margin: 0;
		font-family: inherit;
	}

	p {
		margin: 0;
	}

	.loading {
		color: #94a3b8;
		font-style: italic;
	}

	.sources {
		margin-top: 1rem;
		padding-top: 0.75rem;
		border-top: 1px solid #e2e8f0;
		font-size: 0.85rem;
	}

	.source {
		margin-top: 0.25rem;
		color: #475569;
	}

	.repo {
		font-weight: 600;
		color: #1e40af;
	}

	.score {
		color: #94a3b8;
		margin: 0 0.25rem;
	}

	.files {
		color: #64748b;
		font-size: 0.8rem;
	}
</style>
