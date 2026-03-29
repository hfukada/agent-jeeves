This is a new repository.

This is going to be "The code knowledge base for multi-repository organizations"

Given a GITHUB_TOKEN and an organization name/username, agent-jeeves should clone, and read each repository.
For Each Repository, understand and store:
- Read the README, and generally understand what the repository's purpose is. Generate a summary.
- the languages used in the repository
- the frameworks used in the respository
- the deployment pattern (if it exists)
- the testing commands (if they exist)
- the linting commands (if they exist)
- how to build the docker image (if it exists)
- generate embeddings so that code functionality is generally searchable across the board.

This repository should host a backend server and a frontend
The backend should host:
- an http and mcp server for asking questions.
  - since answers may take time, hand back a query-id, and have clients request the answer by GET'ing the query-id
- an update endpoint, so that humans can update things manually if needed


- frontend should be a simple chat interface for doing the above. Make design decisions as you like. It is only used for searching.

store solid information in postgresql, and embeddings in chromadb. Generate embeddings using ollama nomic-embed-text.
