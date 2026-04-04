const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8080';

export interface GithubRepoPreview {
	full_name: string;
	description: string | null;
	private: boolean;
	default_branch: string;
}

export interface OrgResponse {
	id: string;
	name: string;
}

export interface IndexJobResponse {
	id: string;
	status: 'pending' | 'running' | 'done' | 'error';
	progress: number;
	error: string | null;
}

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

export async function listGithubRepos(org: string, token: string): Promise<GithubRepoPreview[]> {
	const res = await fetch(`${API_URL}/api/github/repos`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ org, token }),
	});
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export async function createOrg(name: string, token: string): Promise<OrgResponse> {
	const res = await fetch(`${API_URL}/api/orgs`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, github_token: token }),
	});
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export async function triggerIndex(
	orgId: string,
	repoNames: string[],
	token: string
): Promise<{ job_id: string }> {
	const res = await fetch(`${API_URL}/api/orgs/${orgId}/index`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ repo_names: repoNames, token }),
	});
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export async function getJob(jobId: string): Promise<IndexJobResponse> {
	const res = await fetch(`${API_URL}/api/jobs/${jobId}`);
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}
