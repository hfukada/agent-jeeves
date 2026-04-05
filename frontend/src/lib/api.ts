const API_URL = 'http://localhost:8686';

export interface QueryResponse {
	id: string;
	question: string;
	status: 'pending' | 'processing' | 'done' | 'error';
	answer: string | null;
	sources: Array<{ repo: string; files: string[]; score: number }>;
	created_at: string;
	completed_at: string | null;
}

export async function submitQuery(question: string): Promise<QueryResponse> {
	const resp = await fetch(`${API_URL}/api/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ question }),
	});
	if (!resp.ok) throw new Error(`Failed to submit query: ${resp.statusText}`);
	return resp.json();
}

export async function getQuery(queryId: string): Promise<QueryResponse> {
	const resp = await fetch(`${API_URL}/api/query/${queryId}`);
	if (!resp.ok) throw new Error(`Failed to get query: ${resp.statusText}`);
	return resp.json();
}

export async function pollQuery(queryId: string, intervalMs = 1000): Promise<QueryResponse> {
	while (true) {
		const result = await getQuery(queryId);
		if (result.status === 'done' || result.status === 'error') {
			return result;
		}
		await new Promise((r) => setTimeout(r, intervalMs));
	}
}
