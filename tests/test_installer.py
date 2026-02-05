"""Tests for installer engine."""

import asyncio

from reincheck.installer import (
    RiskLevel,
    Dependency,
    InstallMethod,
    Preset,
    get_all_dependencies,
    get_dependency,
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
