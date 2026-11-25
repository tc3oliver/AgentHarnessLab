`/app/repo` is a git repository. The commit titled "Tune timeout" set `timeout=0` in `config.ini`, which
breaks the service. Undo that change with a new commit created by `git revert`, without rewriting or
dropping history, and without losing the later "Add log section" commit's change.

When you are done, the working tree must be clean, `timeout` must be back to `30`, and the `[log]` section
must still be there.
