import os
import subprocess
import sys
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from slop_tools import (
    SlopError,
    init_worktree,
    move,
    open_worktree,
    plan_close,
    plan_init,
    plan_move,
    plan_open,
    run_close,
    run_slop,
    run_move,
    run_teardown,
    untracked_paths_from_cwd,
)


@contextmanager
def chdir(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def captured_stderr():
    previous = sys.stderr
    sys.stderr = StringIO()
    try:
        yield sys.stderr
    finally:
        sys.stderr = previous


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def init_repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, stdout=subprocess.DEVNULL)
    git(path, "config", "user.email", "slop@example.test")
    git(path, "config", "user.name", "Slop Tests")
    (path / "README.md").write_text("test repo\n")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "initial")


def init_repo_with_teardown_worktree(root, *, merged=True):
    repo = root / "projects" / "org" / "example-repo"
    init_repo(repo)
    git(repo, "checkout", "-b", "feature")
    (repo / "feature.txt").write_text("feature\n")
    git(repo, "add", "feature.txt")
    git(repo, "commit", "-m", "feature")
    git(repo, "checkout", "main")
    if merged:
        git(repo, "merge", "--no-ff", "feature", "-m", "merge feature")

    worktree = root / "projects" / "org" / "worktrees" / "example-repo" / "feature"
    worktree.parent.mkdir(parents=True)
    git(repo, "worktree", "add", str(worktree), "feature")
    return repo, worktree


class SlopTests(unittest.TestCase):
    def test_maps_nested_project_container(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = (
                root
                / "projects"
                / "org"
                / "worktrees"
                / "example-repo"
                / "ipc-updates"
                / "docs"
                / "note.md"
            )
            source.parent.mkdir(parents=True)
            source.write_text("useful for this branch\n")

            plan = plan_move(source)

            expected = (
                root
                / "projects"
                / "org"
                / "slop"
                / "example-repo"
                / "ipc-updates"
                / "docs"
                / "note.md"
            ).resolve()
            self.assertEqual(plan.destination, expected)

    def test_maps_relative_path_from_inside_worktree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "projects" / "org" / "worktrees" / "repo" / "branch"
            source = worktree / "docs" / "note.md"
            source.parent.mkdir(parents=True)
            source.write_text("relative\n")

            with chdir(worktree):
                plan = plan_move("docs/note.md")

            self.assertEqual(
                plan.destination,
                (root / "projects" / "org" / "slop" / "repo" / "branch" / "docs" / "note.md").resolve(),
            )

    def test_maps_file_using_git_worktree_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktrees" / "repo" / "feature"
            note = worktree / "docs" / "note.md"
            note.parent.mkdir(parents=True)
            note.write_text("useful for now\n")

            subprocess.run(["git", "init"], cwd=worktree, check=True, stdout=subprocess.DEVNULL)

            plan = plan_move(note)

            expected = (root / "slop" / "repo" / "feature" / "docs" / "note.md").resolve()
            self.assertEqual(plan.destination, expected)

    def test_moves_file_to_slop_tree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "worktrees" / "repo" / "branch" / "scratch.md"
            source.parent.mkdir(parents=True)
            source.write_text("temporary\n")

            plan = plan_move(source)
            move(plan)

            self.assertFalse(source.exists())
            self.assertEqual((root / "slop" / "repo" / "branch" / "scratch.md").read_text(), "temporary\n")

    def test_refuses_to_overwrite_without_force(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "worktrees" / "repo" / "branch" / "scratch.md"
            dest = root / "slop" / "repo" / "branch" / "scratch.md"
            source.parent.mkdir(parents=True)
            dest.parent.mkdir(parents=True)
            source.write_text("new\n")
            dest.write_text("old\n")

            with self.assertRaises(SlopError):
                move(plan_move(source))

            self.assertEqual(dest.read_text(), "old\n")

    def test_plans_init_from_base_checkout(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "example-repo"
            init_repo(repo)

            plan = plan_init("ipc-updates", cwd=repo)

            self.assertEqual(plan.repo_name, "example-repo")
            self.assertEqual(plan.source_branch, "main")
            self.assertEqual(
                plan.target,
                (root / "projects" / "org" / "worktrees" / "example-repo" / "ipc-updates").resolve(),
            )

    def test_plans_init_from_managed_worktree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "projects" / "org" / "worktrees" / "example-repo" / "main"
            init_repo(worktree)

            plan = plan_init("ipc-updates", cwd=worktree)

            self.assertEqual(plan.repo_name, "example-repo")
            self.assertEqual(
                plan.target,
                (root / "projects" / "org" / "worktrees" / "example-repo" / "ipc-updates").resolve(),
            )

    def test_creates_worktree_from_local_branch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "example-repo"
            init_repo(repo)

            plan = plan_init("ipc-updates", "main", cwd=repo)
            init_worktree(plan, fetch=False)

            self.assertTrue((plan.target / ".git").exists())
            branch = git(plan.target, "branch", "--show-current").stdout.strip()
            self.assertEqual(branch, "ipc-updates")

    def test_init_requires_local_source_branch(self):
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            init_repo(repo)

            with self.assertRaises(SlopError):
                plan_init("feature", "origin/main", cwd=repo)

    def test_plans_open_existing_local_branch_from_base_checkout(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "example-repo"
            init_repo(repo)
            git(repo, "checkout", "-b", "feature")
            git(repo, "checkout", "main")

            plan = plan_open("feature", cwd=repo)

            self.assertEqual(plan.repo_name, "example-repo")
            self.assertEqual(plan.branch, "feature")
            self.assertEqual(
                plan.target,
                (root / "projects" / "org" / "worktrees" / "example-repo" / "feature").resolve(),
            )

    def test_open_requires_existing_local_branch(self):
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            init_repo(repo)

            with self.assertRaises(SlopError):
                plan_open("missing", cwd=repo)

    def test_opens_worktree_for_existing_local_branch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "example-repo"
            init_repo(repo)
            git(repo, "checkout", "-b", "feature")
            git(repo, "checkout", "main")

            plan = plan_open("feature", cwd=repo)
            open_worktree(plan, fetch=False)

            self.assertTrue((plan.target / ".git").exists())
            branch = git(plan.target, "branch", "--show-current").stdout.strip()
            self.assertEqual(branch, "feature")

    def test_finds_untracked_files_in_current_worktree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "worktrees" / "repo" / "branch"
            init_repo(repo)
            (repo / "tracked.md").write_text("tracked\n")
            git(repo, "add", "tracked.md")
            git(repo, "commit", "-m", "track file")
            (repo / "tracked.md").write_text("modified\n")
            (repo / "docs").mkdir()
            (repo / "docs" / "note with spaces.md").write_text("temporary\n")

            paths = untracked_paths_from_cwd(repo)

            self.assertEqual(paths, [repo.resolve() / "docs" / "note with spaces.md"])

    def test_move_untracked_moves_current_worktree_untracked_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "worktrees" / "repo" / "branch"
            init_repo(repo)
            source = repo / "docs" / "note.md"
            source.parent.mkdir()
            source.write_text("temporary\n")

            with chdir(repo):
                result = run_move(["--untracked"])

            destination = root / "projects" / "org" / "slop" / "repo" / "branch" / "docs" / "note.md"
            self.assertEqual(result, 0)
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_text(), "temporary\n")

    def test_move_requires_paths_or_untracked_flag(self):
        with captured_stderr():
            self.assertEqual(run_move([]), 1)

    def test_slop_requires_explicit_subcommand(self):
        with captured_stderr():
            with self.assertRaises(SystemExit):
                run_slop(["docs/note.md"])

    def test_slop_dispatches_move_subcommand(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "worktrees" / "repo" / "branch" / "scratch.md"
            source.parent.mkdir(parents=True)
            source.write_text("temporary\n")

            result = run_slop(["mv", str(source)])

            self.assertEqual(result, 0)
            self.assertEqual((root / "slop" / "repo" / "branch" / "scratch.md").read_text(), "temporary\n")

    def test_slop_dispatches_open_subcommand(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "org" / "example-repo"
            init_repo(repo)
            git(repo, "checkout", "-b", "feature")
            git(repo, "checkout", "main")

            with chdir(repo):
                result = run_slop(["open", "--no-fetch", "feature"])

            worktree = root / "projects" / "org" / "worktrees" / "example-repo" / "feature"
            self.assertEqual(result, 0)
            self.assertEqual(git(worktree, "branch", "--show-current").stdout.strip(), "feature")

    def test_plans_close_current_managed_worktree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, worktree = init_repo_with_teardown_worktree(root, merged=False)

            plan = plan_close(cwd=worktree)

            self.assertEqual(plan.repo_root, worktree.resolve())
            self.assertEqual(plan.control_repo, repo.resolve())
            self.assertEqual(plan.branch, "feature")

    def test_close_removes_clean_worktree_without_deleting_branch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, worktree = init_repo_with_teardown_worktree(root, merged=False)

            with chdir(worktree):
                result = run_close([])

            branch = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/feature"],
                check=False,
            )
            self.assertEqual(result, 0)
            self.assertFalse(worktree.exists())
            self.assertEqual(branch.returncode, 0)

    def test_slop_dispatches_close_subcommand(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, worktree = init_repo_with_teardown_worktree(root, merged=False)

            with chdir(worktree):
                result = run_slop(["close"])

            branch = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/feature"],
                check=False,
            )
            self.assertEqual(result, 0)
            self.assertFalse(worktree.exists())
            self.assertEqual(branch.returncode, 0)

    def test_teardown_removes_merged_worktree_and_branch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, worktree = init_repo_with_teardown_worktree(root)

            with chdir(worktree):
                result = run_teardown(["--no-fetch"])

            self.assertEqual(result, 0)
            self.assertFalse(worktree.exists())
            branch = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/feature"],
                check=False,
            )
            self.assertNotEqual(branch.returncode, 0)

    def test_teardown_refuses_unmerged_branch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, worktree = init_repo_with_teardown_worktree(root, merged=False)

            with chdir(worktree), captured_stderr():
                result = run_teardown(["--no-fetch"])

            self.assertEqual(result, 1)
            self.assertTrue(worktree.exists())
            branch = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/feature"],
                check=False,
            )
            self.assertEqual(branch.returncode, 0)

    def test_teardown_requires_untracked_files_to_be_slopped_first(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, worktree = init_repo_with_teardown_worktree(root)
            (worktree / "notes.md").write_text("temporary\n")

            with chdir(worktree), captured_stderr():
                result = run_teardown(["--no-fetch"])

            self.assertEqual(result, 1)
            self.assertTrue(worktree.exists())

    def test_teardown_can_slop_untracked_before_removing_worktree(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, worktree = init_repo_with_teardown_worktree(root)
            (worktree / "notes.md").write_text("temporary\n")

            with chdir(worktree):
                result = run_teardown(["--no-fetch", "--slop-untracked"])

            slopped = root / "projects" / "org" / "slop" / "example-repo" / "feature" / "notes.md"
            self.assertEqual(result, 0)
            self.assertFalse(worktree.exists())
            self.assertEqual(slopped.read_text(), "temporary\n")

    def test_teardown_refuses_tracked_changes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, worktree = init_repo_with_teardown_worktree(root)
            (worktree / "feature.txt").write_text("modified\n")

            with chdir(worktree), captured_stderr():
                result = run_teardown(["--no-fetch"])

            self.assertEqual(result, 1)
            self.assertTrue(worktree.exists())


if __name__ == "__main__":
    unittest.main()
