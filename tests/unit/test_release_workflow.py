import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def job(self, name: str) -> str:
        match = re.search(
            rf"^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)",
            self.workflow,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"workflow job {name!r} is missing")
        return match.group("body")

    def test_artifact_job_is_the_only_distribution_producer(self) -> None:
        test_job = self.job("test")
        artifact_job = self.job("artifact")
        clean_install_job = self.job("clean-install")
        release_job = self.job("release")

        self.assertIn("needs: artifact", test_job)
        self.assertIn("actions/download-artifact@v4", test_job)
        self.assertIn("verify-manifest", test_job)
        self.assertNotIn("uv build", test_job)

        self.assertEqual(1, artifact_job.count("uv build"))
        self.assertIn("mkdocs build --strict", artifact_job)
        self.assertIn("verify-distributions", artifact_job)
        self.assertIn("create-release-archives", artifact_job)
        self.assertIn("create-manifest", artifact_job)
        self.assertIn("Verify exact artifact set", artifact_job)
        self.assertIn("actions/upload-artifact@v4", artifact_job)
        self.assertIn("--panel-wheel", artifact_job)

        self.assertIn("needs: artifact", clean_install_job)
        self.assertIn("uv pip install", clean_install_job)
        self.assertNotIn("uv sync", clean_install_job)
        self.assertNotIn("uv build", clean_install_job)

        self.assertIn("needs: [test, artifact, clean-install]", release_job)
        self.assertIn("actions/download-artifact@v4", release_job)
        self.assertIn("verify-manifest", release_job)
        self.assertNotIn("uv build", release_job)
        self.assertIn("dist/manifest.json", release_job)
        self.assertIn("dist/panel-solvers-docs-*.zip", release_job)
        self.assertIn("dist/panel-solvers-examples-*.zip", release_job)

    def test_all_consumers_verify_the_artifact_job_exact_set(self) -> None:
        for job_name in ("test", "clean-install", "release"):
            with self.subTest(job=job_name):
                job = self.job(job_name)
                self.assertIn("actions/download-artifact@v4", job)
                self.assertIn("verify-manifest", job)
        self.assertEqual(1, self.job("artifact").count("create-release-archives"))
        self.assertNotIn("create-release-archives", self.job("release"))

    def test_tag_validation_uses_fetched_protected_main(self) -> None:
        for job_name in ("artifact", "release"):
            with self.subTest(job=job_name):
                job = self.job(job_name)
                self.assertIn("git fetch origin main --tags --force", job)
                self.assertIn("refs/remotes/origin/main^{commit}", job)
                self.assertNotIn('EXPECTED_COMMIT="$(git rev-parse HEAD', job)


if __name__ == "__main__":
    unittest.main()
