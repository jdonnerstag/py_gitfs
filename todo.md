

Interesting information:
https://stackoverflow.com/questions/14872486/retrieve-specific-commit-from-a-remote-git-repository/30701724#30701724

It shows how to reduce download even beyond depth=1, by restricting it to a single branch
It shows that fetch now works on shallow clones as well
It shows that even single commits can be fetched

Use the following to find (on the remote repo?) e.g. the last commit-id before a specific date
git rev-list ... --before=".." --remotes=*remote_name/branch_name
Note, this command runs locally. It does not run on the remote-repo
