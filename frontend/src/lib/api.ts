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

export interface GithubRepoPreview {
	full_name: string;
	description: string | null;
	language: string | null;
	private: boolean;
	html_url: string | null;
}

export interface JobStatus {
	id: string;
	org_id: string;
	status: 'pending' | 'running' | 'done' | 'error';
	error?: string | null;
	progress?: Record<string, unknown>;
}

export async function fetchAvailableRepos(): Promise<GithubRepoPreview[]> {
	const res = await fetch(`${API_URL}/api/github/all-repos`);
	if (!res.ok) {
		const detail = await res.text();
		throw new Error(`Failed to fetch repos (${res.status}): ${detail}`);
	}
	return res.json();
}

export async function registerRepos(fullNames: string[]): Promise<JobStatus> {
	const res = await fetch(`${API_URL}/api/repos/register`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ full_names: fullNames }),
	});
	if (!res.ok) {
		const detail = await res.text();
		throw new Error(`Failed to register repos (${res.status}): ${detail}`);
	}
	return res.json();
}

export async function pollJob(
	jobId: string,
	onProgress?: (status: JobStatus) => void
): Promise<JobStatus> {
	while (true) {
		const res = await fetch(`${API_URL}/api/jobs/${jobId}`);
		if (!res.ok) throw new Error(`Job poll failed (${res.status})`);
		const job: JobStatus = await res.json();
		onProgress?.(job);
		if (job.status === 'done' || job.status === 'error') return job;
		await new Promise((r) => setTimeout(r, 2000));
	}
}
