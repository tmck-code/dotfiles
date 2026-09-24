# Finding an old shelf

Try these in order. Stop at the first confident match:

1. `ls -lt .scratch/`, which lists the shelves with modification times.
2. `.scratch/SESSION.md`, one `<timestamp>|<shelf>|<raw branch>` line per visit. Switch back with the raw branch name.
3. `git branch --sort=-committerdate` or `git reflog`, for branches that have no shelf yet.
4. `git log -1 --format=%s <branch>`. Branch names are short, so a description like "the infra task" often matches only the commit subject.

If nothing matches, or more than one matches, ask the user which task they mean.
