"""Tests for installer engine."""

import asyncio

from reincheck.installer import (
    RiskLevel,
    PresetStatus,
    Dependency,
    DependencyStatus,
    DependencyReport,
    InstallMethod,
    Preset,
    PlanStep,
    Plan,
    get_all_dependencies,
    get_dependency,
    scan_dependencies,
    compute_preset_status,
    get_dependency_report,
    resolve_method,
    plan_install,
    render_plan,
    apply_plan,
)


def test_get_all_dependencies():
    deps = get_all_dependencies()
    assert isinstance(deps, dict)
    assert "mise" in deps
    assert "npm" in deps
    assert "curl" in deps
    assert "uv" in deps
    assert all(isinstance(dep, Dependency) for dep in deps.values())


def test_get_dependency():
    dep = get_dependency("npm")
    assert dep is not None
    assert dep.name == "npm"
    assert dep.check_command == "which npm"

    dep = get_dependency("nonexistent")
    assert dep is None


def test_risk_level_inference():
    from reincheck.installer.dependencies import _infer_risk_level

    assert _infer_risk_level("mise use -g claude-code") == RiskLevel.SAFE
    assert (
        _infer_risk_level("npm install -g @anthropic-ai/claude-code")
        == RiskLevel.INTERACTIVE
    )
    assert (
        _infer_risk_level("curl -fsSL https://example.com | sh") == RiskLevel.DANGEROUS
    )
    assert _infer_risk_level("curl https://example.com | sh") == RiskLevel.DANGEROUS
    assert _infer_risk_level("uv tool install aider-chat") == RiskLevel.INTERACTIVE


def test_resolve_method_preset_default():
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"crush": "npm"},
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    method = resolve_method(preset, "crush", methods)
    assert method.harness == "crush"
    assert method.method_name == "npm"
    assert "npm install" in method.install


def test_resolve_method_with_override():
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"crush": "npm"},
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
        "crush.pnpm": InstallMethod(
            harness="crush",
            method_name="pnpm",
            install="pnpm add -g @crush/agent",
            upgrade="pnpm update -g @crush/agent",
            version="crush --version",
            check_latest="pnpm info @crush/agent version",
            dependencies=["pnpm"],
            risk_level=RiskLevel.SAFE,
        ),
    }

    overrides = {"crush": "pnpm"}
    method = resolve_method(preset, "crush", methods, overrides)
    assert method.method_name == "pnpm"
    assert "pnpm" in method.install


def test_plan_install():
    preset = Preset(
        name="language",
        strategy="language",
        description="Language package managers",
        methods={"crush": "npm", "mistral": "uv"},
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
        "mistral.uv": InstallMethod(
            harness="mistral",
            method_name="uv",
            install="uv tool install mistral-agent",
            upgrade="uv tool upgrade mistral-agent",
            version="mistral --version",
            check_latest="uv tool show mistral-agent | grep version",
            dependencies=["uv"],
            risk_level=RiskLevel.INTERACTIVE,
        ),
    }

    plan = plan_install(preset, ["crush", "mistral"], methods)

    assert plan.preset_name == "language"
    assert len(plan.steps) == 2
    assert plan.steps[0].harness == "crush"
    assert plan.steps[1].harness == "mistral"
    assert plan.steps[0].risk_level == RiskLevel.SAFE
    assert plan.steps[1].risk_level == RiskLevel.INTERACTIVE


def test_render_plan():
    preset = Preset(
        name="language",
        strategy="language",
        description="Language package managers",
        methods={"crush": "npm"},
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    plan = plan_install(preset, ["crush"], methods)
    rendered = render_plan(plan)

    assert "Installation Plan: language" in rendered
    assert "Steps:" in rendered
    assert "crush" in rendered
    assert "npm install" in rendered


def test_render_plan_with_warnings():
    preset = Preset(
        name="test", strategy="test", description="Test", methods={"crush": "dangerous"}
    )

    methods = {
        "crush.dangerous": InstallMethod(
            harness="crush",
            method_name="dangerous",
            install="curl -fsSL https://example.com | sh",
            upgrade="curl -fsSL https://example.com | sh",
            version="crush --version",
            check_latest="curl https://example.com/version",
            dependencies=["curl", "nonexistent"],
            risk_level=RiskLevel.DANGEROUS,
        )
    }

    plan = plan_install(preset, ["crush"], methods)
    rendered = render_plan(plan)

    assert "⚠️  Missing dependencies:" in rendered or len(plan.unsatisfied_deps) == 0
    assert "⚠️  The following require curl|sh" in rendered
    assert "🔴" in rendered


def test_apply_plan_dry_run():
    preset = Preset(
        name="test", strategy="test", description="Test", methods={"crush": "npm"}
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        )
    }

    plan = plan_install(preset, ["crush"], methods)

    async def run_dry_run():
        return await apply_plan(plan, dry_run=True, skip_confirmation=True)

    results = asyncio.run(run_dry_run())

    assert len(results) == 1
    assert results[0].status == "dry-run"
    assert "npm install" in results[0].output


def test_plan_is_ready():
    preset = Preset(
        name="test", strategy="test", description="Test", methods={"crush": "npm"}
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        )
    }

    plan = plan_install(preset, ["crush"], methods)

    assert plan.is_ready() is True


def test_plan_not_ready_with_missing_deps():
    preset = Preset(
        name="test", strategy="test", description="Test", methods={"crush": "npm"}
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["nonexistent_dep"],
            risk_level=RiskLevel.SAFE,
        )
    }

    plan = plan_install(preset, ["crush"], methods)

    assert plan.is_ready() is False
    assert "nonexistent_dep" in plan.unsatisfied_deps


def test_resolve_method_dict_override_missing_commands():
    """Test dict override without 'commands' key uses preset default."""
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"crush": "npm"},
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    overrides = {"crush": {}}
    method = resolve_method(preset, "crush", methods, overrides)
    assert method.method_name == "npm"


def test_resolve_method_fallback_when_preset_method_unavailable():
    """Test fallback_strategy is used when preset method not in methods."""
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"crush": "nonexistent_method"},
        fallback_strategy="npm",
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    method = resolve_method(preset, "crush", methods)
    assert method.method_name == "npm"
    assert method.harness == "crush"


def test_resolve_method_fallback_ignores_harness_not_in_preset():
    """Test fallback works even if harness not in preset.methods."""
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"other": "npm"},
        fallback_strategy="npm",
    )

    methods = {
        "crush.npm": InstallMethod(
            harness="crush",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    method = resolve_method(preset, "crush", methods)
    assert method.method_name == "npm"


def test_resolve_method_raises_error_when_no_valid_method():
    """Test ValueError raised when no method can be resolved."""
    preset = Preset(
        name="test_preset",
        strategy="language",
        description="Test preset",
        methods={"crush": "nonexistent"},
    )

    methods = {
        "other.npm": InstallMethod(
            harness="other",
            method_name="npm",
            install="npm install -g @crush/agent",
            upgrade="npm update -g @crush/agent",
            version="crush --version",
            check_latest="npm info @crush/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        )
    }

    try:
        resolve_method(preset, "crush", methods)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "crush" in str(e)
        assert "test_preset" in str(e)


def test_infer_risk_level_pipe_patterns():
    """Test pipe detection catches various patterns."""
    from reincheck.installer.dependencies import _infer_risk_level

    assert (
        _infer_risk_level("curl -fsSL https://example.com | sh") == RiskLevel.DANGEROUS
    )
    assert _infer_risk_level("curl https://x |bash") == RiskLevel.DANGEROUS
    assert _infer_risk_level("curl|sh") == RiskLevel.DANGEROUS
    assert _infer_risk_level("curl ... |bash -s") == RiskLevel.DANGEROUS
    assert _infer_risk_level("mise use -g claude-code") == RiskLevel.SAFE


def test_dependency_version_extraction(mocker):
    """Test version extraction from various command outputs."""
    dep = Dependency(
        name="test",
        check_command="which test",
        install_hint="Install test",
        version_command="test --version",
    )

    test_cases = [
        ("mise 2024.12.1", "2024.12.1"),
        ("Python 3.11.7", "3.11.7"),
        ("npm 10.8.0", "10.8.0"),
        ("0.0.1770300461", "0.0.1770300461"),
        ("v1.2.3", "1.2.3"),
        ("version 2.0.0", "2.0.0"),
    ]

    for output, expected_version in test_cases:
        result = dep._extract_version(output)
        assert result == expected_version, f"Failed for '{output}': got {result}"


def test_dependency_get_version(mocker):
    """Test get_version() with mocked subprocess."""
    dep = Dependency(
        name="test",
        check_command="which test",
        install_hint="Install test",
        version_command="test --version",
    )

    # Mock subprocess.run for version command
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="test 1.2.3\n", stderr="")

    version = dep.get_version()
    assert version == "1.2.3"
    mock_run.assert_called_once_with(
        "test --version",
        shell=True,
        capture_output=True,
        timeout=5,
        text=True,
    )


def test_dependency_get_version_failure(mocker):
    """Test get_version() handles command failure."""
    dep = Dependency(
        name="test",
        check_command="which test",
        install_hint="Install test",
        version_command="test --version",
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr="error")

    version = dep.get_version()
    assert version is None


def test_dependency_version_satisfied_no_constraints():
    """Test version satisfaction when no min/max specified."""
    dep = Dependency(
        name="test",
        check_command="which test",
        install_hint="Install test",
    )

    assert dep.is_version_satisfied("1.2.3") is True
    assert dep.is_version_satisfied(None) is False


def test_dependency_version_satisfied_with_min(mocker):
    """Test version satisfaction with min_version constraint."""
    dep = Dependency(
        name="test",
        check_command="which test",
        install_hint="Install test",
        min_version="1.2.0",
    )

    assert dep.is_version_satisfied("1.2.0") is True
    assert dep.is_version_satisfied("1.2.3") is True
    assert dep.is_version_satisfied("2.0.0") is True
    assert dep.is_version_satisfied("1.1.9") is False


def test_dependency_status_icon():
    """Test DependencyStatus status_icon property."""
    assert DependencyStatus("test", True, "1.2.3").status_icon == "✅"
    assert (
        DependencyStatus("test", True, None, version_satisfied=False).status_icon == "⚠️"
    )
    assert DependencyStatus("test", False).status_icon == "❌"


def test_scan_dependencies_all(mocker):
    """Test scan_dependencies returns status for all dependencies."""
    mocker.patch("shutil.which", return_value="/usr/bin/test")
    mocker.patch("subprocess.run")

    result = scan_dependencies()
    assert isinstance(result, dict)
    assert all(isinstance(status, DependencyStatus) for status in result.values())
    assert "mise" in result
    assert "npm" in result
    assert "curl" in result
    assert "python" in result


def test_scan_dependencies_with_versions(mocker):
    """Test scan_dependencies populates version information."""

    def mock_which(cmd):
        return f"/usr/bin/{cmd}" if cmd in ["test", "mise"] else None

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=0, stdout="", stderr="")
        if "mise --version" in cmd:
            result.stdout = "mise 2024.12.1"
        return result

    mocker.patch("shutil.which", side_effect=mock_which)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    mise_status = result.get("mise")
    assert mise_status is not None
    assert mise_status.available is True
    assert mise_status.version == "2024.12.1"
    assert mise_status.path == "/usr/bin/mise"


def test_scan_dependencies_failure_scenarios(mocker):
    """Test scan_dependencies handles various failure scenarios."""

    def mock_which(cmd):
        # Only npm is available
        return "/usr/bin/npm" if cmd == "npm" else None

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=1, stdout="", stderr="error")
        # npm version command succeeds
        if "npm --version" in cmd:
            result.returncode = 0
            result.stdout = "10.8.0"
        return result

    mocker.patch("shutil.which", side_effect=mock_which)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    npm_status = result.get("npm")
    assert npm_status is not None
    assert npm_status.available is True
    assert npm_status.version == "10.8.0"

    # Other deps should not be available
    assert result.get("mise") is None or result["mise"].available is False


def test_scan_dependencies_timeout_handling(mocker):
    """Test scan_dependencies handles command timeouts."""

    def mock_run(cmd, **kwargs):
        if "mise --version" in cmd:
            import subprocess

            raise subprocess.TimeoutExpired(cmd, 5)
        return mocker.Mock(returncode=0, stdout="1.0.0", stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/test")
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    # Should still return results even if one command times out
    assert isinstance(result, dict)
    assert len(result) > 0


def test_scan_dependencies_mixed_availability(mocker):
    """Test scan_dependencies with mixed available/unavailable dependencies."""

    def mock_which(cmd):
        return f"/usr/bin/{cmd}" if cmd in ["npm", "uv"] else None

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=0, stdout="", stderr="")
        if "npm --version" in cmd:
            result.stdout = "10.8.0"
        elif "uv --version" in cmd:
            result.stdout = "0.5.0"
        return result

    mocker.patch("shutil.which", side_effect=mock_which)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    assert result["npm"].available is True
    assert result["npm"].version == "10.8.0"
    assert result["uv"].available is True
    assert result["uv"].version == "0.5.0"


def test_compute_preset_status_green(mocker):
    """Test preset status computation with all dependencies satisfied."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test preset",
        methods={"harness1": "npm", "harness2": "uv"},
    )

    methods = {
        "harness1.npm": InstallMethod(
            harness="harness1",
            method_name="npm",
            install="npm install -g foo",
            upgrade="npm update -g foo",
            version="foo --version",
            check_latest="npm info foo version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
        "harness2.uv": InstallMethod(
            harness="harness2",
            method_name="uv",
            install="uv tool install foo",
            upgrade="uv tool upgrade foo",
            version="foo --version",
            check_latest="uv tool show foo",
            dependencies=["uv"],
            risk_level=RiskLevel.SAFE,
        ),
    }

    dep_map = {
        "npm": DependencyStatus("npm", True, "10.8.0", "/usr/bin/npm"),
        "uv": DependencyStatus("uv", True, "0.5.0", "/usr/bin/uv"),
    }

    status = compute_preset_status(preset, methods, dep_map)
    assert status == PresetStatus.GREEN


def test_compute_preset_status_partial(mocker):
    """Test preset status computation with some dependencies satisfied."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test preset",
        methods={"harness1": "npm", "harness2": "cargo"},
    )

    methods = {
        "harness1.npm": InstallMethod(
            harness="harness1",
            method_name="npm",
            install="npm install -g foo",
            upgrade="npm update -g foo",
            version="foo --version",
            check_latest="npm info foo version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
        "harness2.cargo": InstallMethod(
            harness="harness2",
            method_name="cargo",
            install="cargo install foo",
            upgrade="cargo update foo",
            version="foo --version",
            check_latest="cargo search foo",
            dependencies=["cargo"],
            risk_level=RiskLevel.SAFE,
        ),
    }

    dep_map = {
        "npm": DependencyStatus("npm", True, "10.8.0", "/usr/bin/npm"),
        "cargo": DependencyStatus("cargo", False, None, None),
    }

    status = compute_preset_status(preset, methods, dep_map)
    assert status == PresetStatus.PARTIAL


def test_compute_preset_status_red(mocker):
    """Test preset status computation with no dependencies satisfied."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test preset",
        methods={"harness1": "npm"},
    )

    methods = {
        "harness1.npm": InstallMethod(
            harness="harness1",
            method_name="npm",
            install="npm install -g foo",
            upgrade="npm update -g foo",
            version="foo --version",
            check_latest="npm info foo version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
    }

    dep_map = {
        "npm": DependencyStatus("npm", False, None, None),
    }

    status = compute_preset_status(preset, methods, dep_map)
    assert status == PresetStatus.RED


def test_get_dependency_report(mocker):
    """Test dependency report generation."""
    presets = {
        "test_preset": Preset(
            name="test_preset",
            strategy="test",
            description="Test preset",
            methods={"harness1": "npm"},
        )
    }

    methods = {
        "harness1.npm": InstallMethod(
            harness="harness1",
            method_name="npm",
            install="npm install -g foo",
            upgrade="npm update -g foo",
            version="foo --version",
            check_latest="npm info foo version",
            dependencies=["npm"],
            risk_level=RiskLevel.SAFE,
        ),
    }

    dep_map = {
        "npm": DependencyStatus("npm", True, "10.8.0", "/usr/bin/npm"),
        "cargo": DependencyStatus("cargo", False, None, None),
    }

    report = get_dependency_report(presets, methods, dep_map)

    assert isinstance(report, DependencyReport)
    assert report.all_deps == dep_map
    assert len(report.preset_statuses) == 1
    assert report.preset_statuses["test_preset"] == PresetStatus.GREEN
    assert "cargo" in report.missing_deps
    assert report.available_count == 1
    assert report.total_count == 2


def test_get_dependency_report_scans_if_not_provided(mocker):
    """Test get_dependency_report scans if dep_map not provided."""
    presets = {}

    methods = {}

    mocker.patch("shutil.which", return_value="/usr/bin/test")
    mocker.patch("subprocess.run")

    report = get_dependency_report(presets, methods)

    assert isinstance(report, DependencyReport)
    assert len(report.all_deps) > 0  # Should have scanned all built-in deps
    assert report.total_count == len(get_all_dependencies())


def test_render_plan_stability(mocker):
    """Test render_plan produces stable, deterministic output."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test preset",
        methods={"harness1": "safe", "harness2": "interactive"},
    )

    methods = {
        "harness1.safe": InstallMethod(
            harness="harness1",
            method_name="safe",
            install="mise use -g harness1",
            upgrade="mise upgrade -g harness1",
            version="harness1 --version",
            check_latest="mise info harness1",
            dependencies=["mise"],
            risk_level=RiskLevel.SAFE,
        ),
        "harness2.interactive": InstallMethod(
            harness="harness2",
            method_name="interactive",
            install="npm install -g @harness2/agent",
            upgrade="npm update -g @harness2/agent",
            version="harness2 --version",
            check_latest="npm info @harness2/agent version",
            dependencies=["npm"],
            risk_level=RiskLevel.INTERACTIVE,
        ),
    }

    plan = plan_install(preset, ["harness1", "harness2"], methods)

    # Render multiple times and verify consistency
    outputs = [render_plan(plan) for _ in range(3)]

    # All outputs should be identical
    assert outputs[0] == outputs[1] == outputs[2]

    # Verify structure
    assert "Installation Plan: test" in outputs[0]
    assert "Steps:" in outputs[0]
    assert "harness1" in outputs[0]
    assert "harness2" in outputs[0]


def test_render_plan_deterministic_order(mocker):
    """Test render_plan output order follows input order consistently."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test preset",
        methods={"a": "safe", "b": "safe", "c": "safe"},
    )

    methods = {
        "a.safe": InstallMethod(
            harness="a",
            method_name="safe",
            install="install a",
            upgrade="upgrade a",
            version="a --version",
            check_latest="check a",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        ),
        "b.safe": InstallMethod(
            harness="b",
            method_name="safe",
            install="install b",
            upgrade="upgrade b",
            version="b --version",
            check_latest="check b",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        ),
        "c.safe": InstallMethod(
            harness="c",
            method_name="safe",
            install="install c",
            upgrade="upgrade c",
            version="c --version",
            check_latest="check c",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        ),
    }

    # Render with same input order multiple times - should be identical
    order = ["a", "b", "c"]
    plan1 = plan_install(preset, order, methods)
    plan2 = plan_install(preset, order, methods)
    plan3 = plan_install(preset, order, methods)

    output1 = render_plan(plan1)
    output2 = render_plan(plan2)
    output3 = render_plan(plan3)

    # All outputs with same input should be identical (deterministic)
    assert output1 == output2 == output3

    # Different input orders produce different (but deterministic) outputs
    order_cba = ["c", "b", "a"]
    plan_cba = plan_install(preset, order_cba, methods)
    output_cba = render_plan(plan_cba)

    # Different order should produce different output
    assert output1 != output_cba

    # But each is deterministic when run again
    plan_cba2 = plan_install(preset, order_cba, methods)
    output_cba2 = render_plan(plan_cba2)
    assert output_cba == output_cba2


def test_render_plan_no_extra_whitespace(mocker):
    """Test render_plan output doesn't have excessive whitespace."""
    preset = Preset(
        name="test",
        strategy="test",
        description="Test",
        methods={"h1": "safe"},
    )

    methods = {
        "h1.safe": InstallMethod(
            harness="h1",
            method_name="safe",
            install="install h1",
            upgrade="upgrade h1",
            version="h1 --version",
            check_latest="check h1",
            dependencies=[],
            risk_level=RiskLevel.SAFE,
        )
    }

    plan = plan_install(preset, ["h1"], methods)
    output = render_plan(plan)

    # Check for no excessive blank lines
    lines = output.split("\n")
    sum(1 for line in lines if line.strip() == "")

    # Should not have consecutive blank lines
    consecutive_blanks = 0
    for line in lines:
        if line.strip() == "":
            consecutive_blanks += 1
        else:
            consecutive_blanks = 0
        assert consecutive_blanks <= 1, "Found consecutive blank lines"


class TestConfirmInstallation:
    """Tests for confirm_installation function."""

    def _make_plan(
        self,
        unsatisfied_deps=None,
        risky_steps=None,
        harness_count=1,
    ):
        """Helper to create a plan for testing."""
        steps = []
        for i in range(harness_count):
            steps.append(
                PlanStep(
                    harness=f"harness{i}",
                    action="install",
                    command=f"install {i}",
                    timeout=300,
                    risk_level=RiskLevel.SAFE,
                    method_name="safe",
                    dependencies=[],
                )
            )

        return Plan(
            preset_name="test_preset",
            steps=steps,
            unsatisfied_deps=unsatisfied_deps or [],
            risky_steps=risky_steps or [],
        )

    def test_green_preset_no_dangerous_confirms_without_prompt(self, mocker, capsys):
        """Green preset with no dangerous steps should confirm without prompt when skip_confirmation=True."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan()

        # Should return True without prompting
        result = confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=True)

        assert result is True

    def test_green_preset_shows_summary(self, mocker, capsys):
        """Green preset should show installation summary."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(harness_count=3)

        mocker.patch("click.confirm", return_value=True)

        confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=False)

        captured = capsys.readouterr()
        assert "Installation Summary: test_preset" in captured.out
        assert "Harnesses to install: 3" in captured.out

    def test_partial_preset_shows_warning(self, mocker, capsys):
        """Partial preset status should show warning."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(unsatisfied_deps=["missing_dep"])

        mocker.patch("click.confirm", return_value=True)

        confirm_installation(plan, PresetStatus.PARTIAL, skip_confirmation=False)

        captured = capsys.readouterr()
        assert "WARNING: Partial dependencies" in captured.out

    def test_red_preset_shows_warning(self, mocker, capsys):
        """Red preset status should show warning."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(unsatisfied_deps=["dep1", "dep2"])

        mocker.patch("click.confirm", return_value=True)

        confirm_installation(plan, PresetStatus.RED, skip_confirmation=False)

        captured = capsys.readouterr()
        assert "WARNING: Missing dependencies" in captured.out

    def test_dangerous_commands_show_warning(self, mocker, capsys):
        """Dangerous commands should show warning regardless of preset status."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(risky_steps=["risky_harness"])

        mocker.patch("click.confirm", return_value=True)

        confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=False)

        captured = capsys.readouterr()
        assert "DANGEROUS: curl|sh commands detected" in captured.out
        assert "risky_harness" in captured.out

    def test_dangerous_commands_require_confirmation_even_with_skip(self, mocker):
        """Dangerous commands should require confirmation even when skip_confirmation=True."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(risky_steps=["risky_harness"])

        # Even with skip_confirmation=True, should prompt for dangerous
        mock_confirm = mocker.patch("click.confirm", return_value=True)

        result = confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=True)

        assert result is True
        mock_confirm.assert_called_once()
        # Check that the dangerous warning is in the call
        call_args = mock_confirm.call_args[0][0]
        assert "DANGEROUS" in call_args

    def test_user_cancels_returns_false(self, mocker):
        """If user cancels, should return False."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan()

        mocker.patch("click.confirm", return_value=False)

        result = confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=False)

        assert result is False

    def test_non_green_with_skip_still_confirms(self, mocker):
        """Non-green preset should still confirm even with skip_confirmation=True."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(unsatisfied_deps=["missing"])

        mock_confirm = mocker.patch("click.confirm", return_value=True)

        result = confirm_installation(
            plan, PresetStatus.PARTIAL, skip_confirmation=True
        )

        assert result is True
        mock_confirm.assert_called_once()

    def test_shows_missing_dependencies_list(self, mocker, capsys):
        """Should show list of missing dependencies."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(unsatisfied_deps=["npm", "uv"])

        mocker.patch("click.confirm", return_value=True)

        confirm_installation(plan, PresetStatus.RED, skip_confirmation=False)

        captured = capsys.readouterr()
        assert "Missing dependencies:" in captured.out
        assert "npm" in captured.out
        assert "uv" in captured.out

    def test_empty_plan_handles_gracefully(self, mocker):
        """Empty plan should still work."""
        from reincheck.installer import confirm_installation

        plan = self._make_plan(harness_count=0)

        mocker.patch("click.confirm", return_value=True)

        result = confirm_installation(plan, PresetStatus.GREEN, skip_confirmation=False)

        assert result is True


def test_complex_which_command_detection(mocker):
    """Test detection with complex which commands using shell operators."""

    def mock_which(cmd):
        # Only python3 is in PATH (simulating mise scenario where python3 is available)
        if cmd == "python3":
            return "/home/user/.mise/shims/python3"
        return None

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=0, stdout="", stderr="")
        # Complex which command returns path from python3
        if "which python3 || which python" in cmd:
            result.stdout = "/home/user/.mise/shims/python3"
        # Python version command
        elif "python3 --version" in cmd:
            result.stdout = "Python 3.13.0"
        elif "python --version" in cmd:
            result.returncode = 1
        return result

    mocker.patch("shutil.which", side_effect=mock_which)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    # Python should be detected via complex which command
    assert result["python"].available is True
    assert result["python"].version == "3.13.0"
    assert result["python"].path == "/home/user/.mise/shims/python3"


def test_simple_vs_complex_which_commands(mocker):
    """Test that simple and complex which commands are handled correctly."""

    def mock_which(cmd):
        if cmd == "npm":
            return "/usr/bin/npm"
        elif cmd == "python3":
            return None  # Not in PATH
        return None

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=0, stdout="", stderr="")
        # Simple which: npm
        if "npm --version" in cmd:
            result.stdout = "10.8.0"
        # Complex which: python
        elif "which python3 || which python" in cmd:
            result.stdout = "/home/user/.local/bin/python"
        elif "python --version" in cmd:
            result.stdout = "Python 3.11.0"
        return result

    mocker.patch("shutil.which", side_effect=mock_which)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    # Simple which should use shutil.which
    assert result["npm"].available is True
    assert result["npm"].version == "10.8.0"
    assert result["npm"].path == "/usr/bin/npm"

    # Complex which should use subprocess
    assert result["python"].available is True
    assert result["python"].version == "3.11.0"
    assert result["python"].path == "/home/user/.local/bin/python"


def test_path_validation_with_multiline_output(mocker):
    """Test that path extraction handles multi-line output correctly."""

    def mock_run(cmd, **kwargs):
        result = mocker.Mock(returncode=0, stdout="", stderr="")
        # Simulate multi-line output (e.g., from which with verbose flags)
        if "which python3 || which python" in cmd:
            result.stdout = (
                "/home/user/.mise/shims/python\n/home/user/.mise/shims/python3\n"
            )
        elif "python3 --version" in cmd:
            result.stdout = "Python 3.13.0"
        return result

    mocker.patch("shutil.which", return_value=None)
    mocker.patch("subprocess.run", side_effect=mock_run)

    result = scan_dependencies()

    # Should take only the first line
    assert result["python"].available is True
    assert result["python"].path == "/home/user/.mise/shims/python"


def test_helper_functions():
    """Test helper functions for which command handling."""
    from reincheck.installer.dependencies import (
        _is_simple_which_command,
        _extract_binary_from_which,
    )

    # Test _is_simple_which_command
    assert _is_simple_which_command("which python") is True
    assert _is_simple_which_command("which python3") is True
    assert _is_simple_which_command("which python3 || which python") is False
    assert _is_simple_which_command("which python 2>/dev/null") is False
    assert _is_simple_which_command("not a which command") is False

    # Test _extract_binary_from_which
    assert _extract_binary_from_which("which python") == "python"
    assert _extract_binary_from_which("which python3") == "python3"
    assert _extract_binary_from_which("which python3 || which python") is None
    assert _extract_binary_from_which("not a which command") is None
