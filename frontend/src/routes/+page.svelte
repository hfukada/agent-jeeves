<script lang="ts">
	import ChatInput from '$lib/components/ChatInput.svelte';
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import SetupFlow from '$lib/components/SetupFlow.svelte';
	import { submitQuery, pollQuery, type QueryResponse } from '$lib/api';

	interface Message {
		question: string;
		response: QueryResponse | null;
	}

	let orgId = $state<string | null>(null);
	let messages = $state<Message[]>([]);
	let loading = $state(false);

	async function handleSubmit(question: string) {
		const msg: Message = { question, response: null };
		messages = [...messages, msg];
		loading = true;

		try {
			const submitted = await submitQuery(question);
			msg.response = submitted;
			messages = [...messages.slice(0, -1), msg];

			const result = await pollQuery(submitted.id);
			msg.response = result;
			messages = [...messages.slice(0, -1), msg];
		} catch (err) {
			msg.response = {
				id: '',
				question,
				status: 'error',
				answer: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
				sources: [],
				created_at: new Date().toISOString(),
				completed_at: new Date().toISOString(),
			};
			messages = [...messages.slice(0, -1), msg];
		} finally {
			loading = false;
		}
	}
</script>

{#if orgId === null}
	<SetupFlow oncomplete={(id) => { orgId = id; }} />
{:else}
	<div class="chat-container">
		<div class="messages">
			{#if messages.length === 0}
				<div class="empty">
					<p>Search across your organization's repositories.</p>
					<p class="hint">Try: "Which repos use FastAPI?" or "Where is authentication handled?"</p>
				</div>
			{/if}

			{#each messages as message}
				<ChatMessage {message} />
			{/each}
		</div>

		<ChatInput onSubmit={handleSubmit} disabled={loading} />
	</div>
{/if}

<style>
	.chat-container {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
	}

	.empty {
		text-align: center;
		color: #94a3b8;
		padding: 4rem 1rem;
	}

	.empty p {
		margin: 0.5rem 0;
	}

	.hint {
		font-size: 0.85rem;
		font-style: italic;
	}
</style>
