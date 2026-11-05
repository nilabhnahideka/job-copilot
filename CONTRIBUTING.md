# Contributing

The rules this project follows, so the code and its history stay easy to understand.

## Commit messages

Every commit uses the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<area>): <what changed, in a few words>

<why it changed, and anything a reader should know. Plain English.>
```

**Types**

| Type | Use it for |
|---|---|
| `feat` | A new feature the user can see or use |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `test` | Adding or changing tests |
| `refactor` | Restructuring code without changing what it does |
| `chore` | Tooling, dependencies, config |

**Areas:** `agent`, `api`, `web`, `profile`, `search`, `apply`, `deploy`, `docs`, `ci`.

**Example**

```
feat(profile): save job preferences

Adds a form where you set job titles, cities and salary range.
Job search will use these, so you only enter them once.
```

Keep each commit focused on one thing.

## Documentation

Every change updates the docs it affects, in the same commit:

- **Every code file** starts with a comment saying what it's for.
- **Tricky code** gets a comment explaining *why* it's written that way (not *what* it does, which the code already shows).
- **`CHANGELOG.md`**: add a line under "Unreleased".
- **`docs/decisions.md`**: add an entry when choosing a library, a service or an approach.
- **`docs/architecture.md`**: update it when parts, steps or data storage change.
- **`README.md`**: update it when setup, features or the API change.

## Before you push

Run the same checks as CI:

```bash
cd backend && ruff check . && pytest -q
cd ../frontend && npm run lint && npm run build
```
