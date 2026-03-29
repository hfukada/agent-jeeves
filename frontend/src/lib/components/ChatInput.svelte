<script lang="ts">
	let { onSubmit, disabled = false }: { onSubmit: (text: string) => void; disabled?: boolean } =
		$props();
	let input = $state('');

	function handleSubmit(e: Event) {
		e.preventDefault();
		const text = input.trim();
		if (!text || disabled) return;
		onSubmit(text);
		input = '';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			handleSubmit(e);
		}
	}
</script>

<form class="chat-input" onsubmit={handleSubmit}>
	<textarea
		bind:value={input}
		onkeydown={handleKeydown}
		placeholder="Search across repositories..."
		rows="2"
		{disabled}
	></textarea>
	<button type="submit" disabled={disabled || !input.trim()}>Search</button>
</form>

<style>
	.chat-input {
		display: flex;
		gap: 0.75rem;
		padding: 1rem;
		border-top: 1px solid #e2e8f0;
		background: #fff;
	}

	textarea {
		flex: 1;
		padding: 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		font-family: inherit;
		font-size: 0.95rem;
		resize: none;
		outline: none;
	}

	textarea:focus {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
	}

	button {
		padding: 0.75rem 1.5rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		align-self: flex-end;
	}

	button:hover:not(:disabled) {
		background: #2563eb;
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
