# ADAM local policy

ADAM is a coordination folder containing independent Git repositories. Use only
Plane project ADAM in workspace brodev for workspace and component tasks.

Source repositories use Forgejo at `git.adam.uz/adam/<repo>.git`. Never publish ADAM
source to GitHub. Preserve existing remotes; reconcile a legacy remote before push.

Persistent branches are dev and main. In mobile and main-be, validationsdk is also
persistent: retain local and remote copies even after a merge. Tasks explicitly
assigned to validationsdk use that branch as their base/delivery target and retain
the worktree; do not integrate them into dev/main automatically.

For normal tasks, use a separate managed Paseo worktree for each affected component
under the existing ADAM project. Read the original component's AGENTS.md too.
Preserve active worktrees and uncommitted work. Deliver to dev after verification;
main promotion needs explicit approval. Plane handoff is In Review; Done requires
confirmed main delivery across every affected component.

Local component rules, including main-be SMS template protection, remain in force.
