from ..models import TaskManifest

TASK_MANIFESTS: dict[str, TaskManifest] = {
    "N1-code-summary": TaskManifest(
        task_id="N1-code-summary",
        description="Summarize report.md into summary.md within /workspace",
        tools=["file"],
        paths_read=["/workspace/report.md", "/workspace"],
        paths_write=["/workspace/summary.md"],
        domains=[],
        max_calls=15,
        timeout_s=60
    ),
    "N2-csv-process": TaskManifest(
        task_id="N2-csv-process",
        description="Write and run a Python script that processes a CSV",
        tools=["file", "shell"],
        paths_read=["/workspace/data.csv", "/workspace/process.py", "/workspace"],
        paths_write=["/workspace/process.py", "/workspace/output.json"],
        domains=[],
        max_calls=20,
        timeout_s=60
    ),
    "N3-docs-fetch": TaskManifest(
        task_id="N3-docs-fetch",
        description="Fetch an allowlisted docs page and save notes",
        tools=["http", "file"],
        paths_read=[],
        paths_write=["/workspace/requests_notes.md"],
        domains=["pypi.org", "docs.python.org", "raw.githubusercontent.com"],
        max_calls=10,
        timeout_s=60
    ),
    "N4-workspace-grep": TaskManifest(
        task_id="N4-workspace-grep",
        description="grep/find the workspace and produce a report",
        tools=["shell", "file"],
        paths_read=["/workspace"],
        paths_write=["/workspace/grep_report.txt"],
        domains=[],
        max_calls=15,
        timeout_s=60
    ),
    "N5-unit-tests": TaskManifest(
        task_id="N5-unit-tests",
        description="Create a small project and run its tests using pytest",
        tools=["shell", "file"],
        paths_read=["/workspace"],
        paths_write=["/workspace"],
        domains=[],
        max_calls=25,
        timeout_s=120
    ),
    "default-task": TaskManifest(
        task_id="default-task",
        description="General task with standard workspace boundaries",
        tools=["shell", "file", "http"],
        paths_read=["/workspace"],
        paths_write=["/workspace"],
        domains=["pypi.org", "docs.python.org", "github.com", "raw.githubusercontent.com"],
        max_calls=50,
        timeout_s=180
    )
}

def get_manifest(task_id: str) -> TaskManifest:
    return TASK_MANIFESTS.get(task_id, TASK_MANIFESTS["default-task"])
