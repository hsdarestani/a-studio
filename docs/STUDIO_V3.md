# A+ Studio V3

Studio V3 adds a real source-code workspace to the existing managed builder.

## Code Agent V3

- Edits UTF-8 HTML, CSS, JavaScript, JSON, manifest and text files.
- Keeps project code under the Studio app-data volume, isolated by project slug.
- Snapshots the previous workspace before every AI or manual edit.
- Validates paths, file count, file size and blocked executable/hidden file types.
- Parses JavaScript with `node --check` before a revision can replace the current workspace.
- Rejects `eval`, `new Function`, `javascript:` URLs and remote executable script tags.
- Rebuilds only the preview directory; production is unchanged until explicit publish.
- Syncs nested source files into the project's private GitHub repository when GitHub provisioning is configured.

## IDE

Code Agent projects expose three workspace views:

1. Chat — AI edits real files and returns the changed file list.
2. Code — authenticated file tree, editor and zero-credit manual save-to-preview flow.
3. Changes — revision history with server-generated unified text diffs.

The live preview remains visible beside the workspace and can be refreshed independently.

## Executable sandbox

The V3 web workspace deliberately does not execute generated application code on the Django/Celery host. Static web code can be generated and previewed without the executable sandbox. Framework/package builds continue to use the separately configured HMAC-authenticated sandbox service when available.
