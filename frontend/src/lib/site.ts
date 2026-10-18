// Single source of truth for repository and documentation URLs

const detectedRepoUrl = "https://github.com/ajayg10/hindsight";

export const REPO_URL =
  process.env.NEXT_PUBLIC_REPO_URL || detectedRepoUrl;

export const DOCS_URL = `${REPO_URL}/tree/main/docs`;