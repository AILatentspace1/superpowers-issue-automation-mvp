import tempfile
import unittest
from pathlib import Path

from scripts import local_superpowers_orchestrator as orch


class TargetRepoStorageTests(unittest.TestCase):
    def test_state_and_artifact_paths_are_inside_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_root = Path(tmp) / "target-repo"
            state = {"repo": "OWNER/target-repo", "issue": "42"}

            self.assertEqual(
                orch.state_path(target_root, 42),
                target_root / ".superpowers" / "issues" / "issue-42.yaml",
            )
            self.assertEqual(
                orch.artifact_path(target_root, state, "goal"),
                target_root / ".superpowers" / "runs" / "issue-42" / "goal.md",
            )

    def test_artifact_url_points_to_target_repo_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_root = Path(tmp) / "target-repo"
            artifact = target_root / ".superpowers" / "runs" / "issue-42" / "goal.md"

            self.assertEqual(
                orch.github_blob_url("OWNER/target-repo", "feature", target_root, artifact),
                "https://github.com/OWNER/target-repo/blob/feature/.superpowers/runs/issue-42/goal.md",
            )

    def test_dry_run_missing_target_repo_does_not_clone_or_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target_root = workspace / "missing-repo"

            resolved = orch.resolve_target_repo("OWNER/missing-repo", workspace_root=workspace, apply=False)

            self.assertEqual(resolved, target_root)
            self.assertFalse(target_root.exists())

    def test_repo_url_normalization_accepts_ssh_and_https(self):
        self.assertEqual(
            orch.normalize_repo_url("git@github.com:OWNER/target-repo.git"),
            "OWNER/target-repo",
        )
        self.assertEqual(
            orch.normalize_repo_url("https://github.com/OWNER/target-repo.git"),
            "OWNER/target-repo",
        )


if __name__ == "__main__":
    unittest.main()
