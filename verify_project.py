import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def run_command(command: list[str], cwd: Path = ROOT, timeout: int = 120) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout


def check_file(path: str) -> CheckResult:
    target = ROOT / path
    return CheckResult(
        name=f"file exists: {path}",
        ok=target.exists(),
        detail=str(target),
    )


def check_json(path: str) -> CheckResult:
    target = ROOT / path
    try:
        json.loads(target.read_text(encoding="utf-8"))
        return CheckResult(f"valid json: {path}", True, "loaded")
    except Exception as exc:
        return CheckResult(f"valid json: {path}", False, repr(exc))


def check_tests() -> CheckResult:
    code, output = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    return CheckResult(
        "unit tests",
        code == 0 and "Ran 16 tests" in output and "OK" in output,
        output.strip().splitlines()[-1] if output.strip() else "no output",
    )


def check_template_list() -> CheckResult:
    code, output = run_command([sys.executable, "builder_demo.py", "--list-templates"])
    ok = (
        code == 0
        and "outfit_recommendation_template.json" in output
        and "commute_outfit_template.json" in output
    )
    return CheckResult("builder lists multiple templates", ok, output.strip())


def check_web_frontend() -> CheckResult:
    code, output = run_command(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "import web_app; "
                "index = web_app.index_bytes().decode('utf-8'); "
                "detail = web_app.api_template_detail('outfit_recommendation_template.json'); "
                "assert '/static/app.js' in index; "
                "assert 'nodes-container' in index; "
                "assert any(node['id'] == 'question' for node in detail['nodes']); "
                "assert detail['generated_config']['execution']['type'] == 'sequential'; "
                "print('web frontend API/static OK')"
            ),
        ]
    )
    return CheckResult("visual web frontend render", code == 0, output.strip())


def check_generated_workflow(name: str, command: list[str], expected: str) -> CheckResult:
    code, output = run_command(command, timeout=180)
    ok = code == 0 and "Workflow Trace (6 Nodes)" in output and "Question Node" in output and expected in output
    return CheckResult(name, ok, "exit=" + str(code))


def check_external_tools() -> list[CheckResult]:
    results: list[CheckResult] = []

    npm = shutil.which("npm")
    if npm:
        code, output = run_command([npm, "run", "version"], cwd=ROOT / "external_tools" / "flowise_poc")
        results.append(
            CheckResult(
                "Flowise package version check",
                code == 0 and "3.1.2" in output,
                output.strip(),
                required=False,
            )
        )
    else:
        results.append(CheckResult("Flowise package version check", False, "npm not found", required=False))

    code, output = run_command([sys.executable, "-m", "pip", "index", "versions", "langflow"])
    results.append(
        CheckResult(
            "Langflow package index check",
            code == 0 and "langflow (1.9.4)" in output,
            output.strip().splitlines()[0] if output.strip() else "no output",
            required=False,
        )
    )

    docker = shutil.which("docker")
    results.append(
        CheckResult(
            "Dify Docker availability check",
            docker is not None,
            docker or "Docker not installed; documented in external_tools/dify_poc/README.md",
            required=False,
        )
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Builder MVP deliverables.")
    parser.add_argument("--external", action="store_true", help="also check external tool package availability")
    args = parser.parse_args()

    required_files = [
        "run_builder_app.cmd",
        "run_desktop.cmd",
        "run_web.cmd",
        "run_verify.cmd",
        "builder_app.py",
        "builder_demo.py",
        "web_app.py",
        "workflow_builder_preview.html",
        "configs/builder_templates/outfit_recommendation_template.json",
        "configs/builder_templates/commute_outfit_template.json",
        "src/agent_builder/template_builder.py",
        "deliverables/mentor_requirement_alignment_zh.md",
        "deliverables/builder_tool_comparison_kr.md",
        "deliverables/external_builder_tool_verification_zh.md",
        "external_tools/flowise_poc/package.json",
        "external_tools/dify_poc/README.md",
        "external_tools/langflow_poc/README.md",
        "external_tools/flowise_poc/run_flowise_poc.cmd",
        "external_tools/dify_poc/run_dify_poc.cmd",
        "external_tools/langflow_poc/run_langflow_poc.cmd",
    ]
    json_files = [
        "configs/outfit_agent.json",
        "configs/outfit_workflow.json",
        "configs/flowise_poc_mapping.json",
        "configs/builder_templates/outfit_recommendation_template.json",
        "configs/builder_templates/commute_outfit_template.json",
    ]

    results: list[CheckResult] = []
    results.extend(check_file(path) for path in required_files)
    results.extend(check_json(path) for path in json_files)
    results.append(check_tests())
    results.append(check_template_list())
    results.append(check_web_frontend())
    results.append(
        check_generated_workflow(
            "generated travel/outfit workflow",
            [
                sys.executable,
                "builder_demo.py",
                "--run-generated",
                "칭다오 다음 주 여행 캐주얼 옷 추천해줘",
                "--user",
                "user_a",
            ],
            "추천 순위",
        )
    )
    results.append(
        check_generated_workflow(
            "generated commute/work workflow",
            [
                sys.executable,
                "builder_demo.py",
                "--run-generated",
                "--builder-template",
                "configs\\builder_templates\\commute_outfit_template.json",
                "서울 내일 출근 포멀 옷 추천해줘",
                "--user",
                "user_b",
            ],
            "추천 순위",
        )
    )
    if args.external:
        results.extend(check_external_tools())

    failed_required = [result for result in results if result.required and not result.ok]

    print("Builder MVP Verification")
    print("=" * 64)
    for result in results:
        marker = "PASS" if result.ok else ("INFO" if not result.required else "FAIL")
        print(f"[{marker}] {result.name}")
        if result.detail:
            print(f"       {result.detail[:500]}")

    print("=" * 64)
    if failed_required:
        print(f"FAILED required checks: {len(failed_required)}")
        return 1
    print("All required checks passed.")
    if args.external:
        print("External checks are informational because local tool availability can vary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
