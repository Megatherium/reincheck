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
    from reincheck.installer import _infer_risk_level

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
    from reincheck.installer import _infer_risk_level

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
