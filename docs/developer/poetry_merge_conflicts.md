# Poetry Merge Conflicts

A common merge conflict that needs to be resolved are conflicts with `pyproject.toml` and `poetry.lock`, the two files that controls the project's dependencies. Conflicts from `pyproject.toml` are typically your average conflict, caused by two competing changes on a particular line. These can be resolved as normal - use common sense and some context to determine which changes need to be kept and where relevant, changes from each branch need to be combined.

Conflicts on `poetry.lock` are typically caused by very minor version bumps to dependencies. If a dependabot PR is merged, this will often cause merge conflicts on open PRs that don't contain the same minor version bump to the affected dependency. Luckily, these conflicts can be easily resolved - delete the lock file and regenerate it with a `poetry` command. The below instructions are a good guide to follow in these situations:

1. Resolve merge conflicts in `pyproject.toml`
2. Delete `poetry.lock`
3. Run `poetry lock` to regenerate the lock file
4. Continue resolving additional conflicts or commit the changes as part of the merge commit
