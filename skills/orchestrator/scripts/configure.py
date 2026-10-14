#!/usr/bin/env python3
"""M1 readonly project registration and configuration preparation (stdlib only)."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class ConfigError(ValueError):
    pass


SECRET = re.compile(
    r"(?i)(?:\b(?:sk-|gh[pousr]_|github_pat_|AKIA)[A-Za-z0-9_-]{8,}"
    r"|\b(?:bearer|basic|digest)\s+\S+"
    r"|(?:api[_-]?key|token|password|passwd|secret)\s*[:=]\s*\S+"
    r"|\b[a-z][a-z0-9+.-]*://[^/\s@]+@"
    r"|(?<!\S)--(?:user|proxy-user|password|passwd|token|api-key|secret)(?:=|\s+)\S+"
    r"|(?<!\S)-[uU](?:\s+)?[^\s]+)"
)
ID = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
COMMON = {"execution", "harnesses", "skills", "roles", "workflow", "template", "policies"}
NATIVE = {
    "claude": [
        {"--model": "fable", "--permission-mode": "bypassPermissions"},
        {"--model": "fable", "--permission-mode": "manual"},
    ],
    "codex": [
        {"--yolo": True, "--model": "gpt-6.1-sol"},
        {"--no-daemon": True, "--yolo": True, "--model": "gpt-6.1-sol"},
        {"--profile": "herdr", "--model": "gpt-5.6-sol"},
    ],
}


def fail(message):
    raise ConfigError(message)


def fields(value, allowed, where, required=()):
    if not isinstance(value, dict):
        fail(f"{where}: expected a mapping")
    if set(value) - set(allowed):
        fail(f"{where}: unknown field; allowed: {', '.join(sorted(allowed))}")
    if set(required) - set(value):
        fail(f"{where}: missing required fields: {', '.join(sorted(set(required) - set(value)))}")


def text(value, where):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 and c != '\n' for c in value):
        fail(f"{where}: expected nonempty text")
    if SECRET.search(value):
        fail(f"{where}: credential-like content is not allowed")
    return value


def identifier(value, where):
    if not isinstance(value, str) or not ID.fullmatch(value):
        fail(f"{where}: expected a lowercase identifier (max 48 characters)")
    return value


def texts(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        fail(f"{where}: expected {'nonempty ' if nonempty else ''}list")
    for item in value:
        text(item, where)
    if len(value) != len(set(value)):
        fail(f"{where}: duplicate entries")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("configuration: duplicate mapping key")
        result[key] = value
    return result


def load(path, with_hash=False, raw=None):
    try:
        raw = path.read_bytes() if raw is None else raw
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
        return (value, hashlib.sha256(raw).hexdigest()) if with_hash else value
    except (OSError, UnicodeError):
        fail(f"cannot read configuration: {path}")
    except json.JSONDecodeError as exc:
        fail(f"{path}: expected JSON syntax (the supported YAML subset), line {exc.lineno}")


def validate_layer(config, layer):
    extra = {"global": {"assets_root"}, "project": {"project"},
             "run": {"objective", "worker_role", "context_refs"}}[layer]
    fields(config, COMMON | extra, layer)
    if "assets_root" in config:
        text(config["assets_root"], "assets_root")
    if "execution" in config:
        fields(config["execution"], {"backend"}, "execution")
        if config["execution"].get("backend", "herdr") != "herdr":
            fail("execution.backend: only herdr is supported")
    schemas = {
        "harnesses": {"kind", "start_args"},
        "skills": {"directory"},
        "roles": {"definition", "harness", "skills"},
    }
    for group, allowed in schemas.items():
        if group not in config:
            continue
        if not isinstance(config[group], dict):
            fail(f"{group}: expected a mapping")
        for name, item in config[group].items():
            identifier(name, group)
            fields(item, allowed, f"{group}.{name}")
            for key, value in item.items():
                if key in {"start_args", "skills"}:
                    texts(value, f"{group}.{name}.{key}", True)
                else:
                    text(value, f"{group}.{name}.{key}")
            if group == "harnesses":
                if "kind" in item and item["kind"] not in NATIVE:
                    fail(f"harnesses.{name}: unsupported kind")
                if "start_args" in item:
                    parse_args(item["start_args"], item.get("kind"))
    for key in ("workflow", "template", "objective", "worker_role"):
        if key in config:
            text(config[key], key)
    if "context_refs" in config:
        texts(config["context_refs"], "context_refs", True)
    if "policies" in config:
        p = config["policies"]
        fields(p, {"allowed_paths", "require_approval", "require_review"}, "policies")
        if "allowed_paths" in p:
            texts(p["allowed_paths"], "policies.allowed_paths", True)
            for value in p["allowed_paths"]:
                relative(value)
        if "require_approval" in p:
            texts(p["require_approval"], "policies.require_approval")
            if set(p["require_approval"]) - {"write", "network", "git_mutation"}:
                fail("policies.require_approval: unsupported action")
        if "require_review" in p and type(p["require_review"]) is not bool:
            fail("policies.require_review: expected boolean")
    if "project" in config:
        p = config["project"]
        required = {"id", "repository", "validation_commands", "scope", "rules", "resources"}
        fields(p, required | {"rule_support_files"}, "project", required)
        if "rule_support_files" in p:
            texts(p["rule_support_files"], "project.rule_support_files")
        identifier(p["id"], "project.id")
        text(p["repository"], "project.repository")
        for key in ("validation_commands", "scope", "rules"):
            texts(p[key], f"project.{key}", key == "scope")
        # M1 has no mutable test services. Do not pretend to provision isolation.
        if p["resources"] != {"mode": "none"}:
            fail("project.resources: M1 supports only {mode: none}")


def parse_args(args, kind=None):
    texts(args, "start_args", True)
    pairs, index = {}, 0
    while index < len(args):
        option = args[index]
        if option in pairs:
            fail("start_args: duplicate native option")
        if option in {"--yolo", "--no-daemon"}:
            pairs[option] = True
            index += 1
        else:
            if index + 1 >= len(args) or args[index + 1].startswith("--"):
                fail("start_args: missing native option value")
            pairs[option] = args[index + 1]
            index += 2
    candidates = NATIVE[kind] if kind in NATIVE else [p for group in NATIVE.values() for p in group]
    if pairs not in candidates:
        fail("start_args: unsupported native arguments; use an explicitly supported M1 combination")
    return pairs


def relative(value):
    text(value, "relative path")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or value.startswith("~"):
        fail("path: expected a relative path without parent traversal")
    return p.as_posix()


def inside(path, root):
    return path == root or root in path.parents


def resolve(path, base):
    p = Path(path).expanduser()
    return (p if p.is_absolute() else base / p).resolve()


def member(root, ref, directory=False):
    p = (root / relative(ref)).resolve()
    if not inside(p, root):
        fail(f"path escapes its declared root: {ref}")
    if not (p.is_dir() if directory else p.is_file()):
        fail(f"missing required {'directory' if directory else 'file'}: {ref}")
    return p


def git(repo, *args):
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                                text=True, timeout=10, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except (OSError, subprocess.TimeoutExpired):
        fail("project: Git capability unavailable")
    if result.returncode:
        fail("project: requires an existing readable Git repository with a baseline commit")
    return result.stdout.strip()


def project_info(config, base):
    fields(config, COMMON | {"project"}, "project layer", {"project"})
    p = config["project"]
    repo = resolve(p["repository"], base)
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        fail("project.repository: must name the Git root, not a nested directory")
    git(repo, "rev-parse", "HEAD")
    for ref in p["scope"]:
        target = (repo / relative(ref)).resolve()
        if not inside(target, repo) or not target.exists():
            fail("project.scope: missing or escaping path")
    for ref in p["rules"] + p.get("rule_support_files", []):
        member(repo, ref)
    return repo


def merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def under(ref, prefix):
    return inside(Path(ref), Path(prefix))


def policy_merge(layers, repo):
    paths, approvals, review = ["."], set(), False
    for layer in layers:
        p = layer.get("policies", {})
        if "allowed_paths" in p:
            requested = []
            for value in p["allowed_paths"]:
                target = (repo / relative(value)).resolve()
                if not inside(target, repo):
                    fail("policies.allowed_paths: path escapes repository")
                requested.append(target.relative_to(repo).as_posix())
            paths = sorted({b if under(b, a) else a for a in paths for b in requested
                            if under(a, b) or under(b, a)})
            if not paths:
                fail("policies.allowed_paths: empty intersection")
        approvals.update(p.get("require_approval", []))
        review = review or p.get("require_review", False)
    return {"allowed_paths": paths, "require_approval": sorted(approvals), "require_review": review}


def output_path(home, relative_path, repo):
    destination = home / relative_path
    actual = destination.resolve()
    if not inside(actual, home) or inside(actual, repo):
        fail("output path escapes the external state home")
    return destination


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def register(home, source):
    config = load(source)
    validate_layer(config, "project")
    repo = project_info(config, source.parent)
    if inside(home, repo):
        fail("state home must be outside the business repository")
    config["project"]["repository"] = str(repo)
    destination = output_path(home, Path("projects") / (config["project"]["id"] + ".yaml"), repo)
    if destination.exists() or destination.is_symlink():
        fail("project registration already exists; nothing was overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    save(destination, config)
    return {"registration": str(destination), "repository": str(repo)}


def resolve_configuration(home, global_path, project_id, run_path, run_id, workspace=None, workers=None):
    project_path = home / "projects" / (identifier(project_id, "project id") + ".yaml")
    source_paths = [global_path, project_path, run_path]
    loaded = [load(p, with_hash=True) for p in source_paths]
    layers = [value for value, digest in loaded]
    for layer, name in zip(layers, ["global", "project", "run"]):
        validate_layer(layer, name)
    fields(layers[0], COMMON | {"assets_root"}, "global", COMMON | {"assets_root"})
    fields(layers[2], COMMON | {"objective", "worker_role", "context_refs"}, "run",
           {"objective", "worker_role", "context_refs"})
    registered_repo = project_info(layers[1], project_path.parent)
    repo = registered_repo if workspace is None else workspace.resolve()
    if workspace is not None:
        if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
            fail("workspace: must name a Git worktree root")
        common = lambda p: resolve(git(p, "rev-parse", "--git-common-dir"), p)
        if repo == registered_repo or common(repo) != common(registered_repo):
            fail("workspace: must be a separate worktree of the registered repository")
    if layers[1]["project"]["id"] != project_id:
        fail("project registration identity mismatch")
    if inside(home, repo):
        fail("state home must be outside the business repository")
    config = merge(merge(layers[0], layers[1]), layers[2])
    fields(config["execution"], {"backend"}, "execution", {"backend"})
    config["policies"] = policy_merge(layers, repo)
    assets = resolve(config["assets_root"], global_path.parent)
    config["assets_root"] = str(assets)
    config["project"]["repository"] = str(registered_repo)
    worker = config["worker_role"]
    if worker == "manager" or worker not in config["roles"]:
        fail("worker_role: must reference a configured worker, not manager")
    if "manager" not in config["roles"]:
        fail("roles.manager is required")
    for name, harness in config["harnesses"].items():
        fields(harness, {"kind", "start_args"}, f"harnesses.{name}", {"kind", "start_args"})
        parse_args(harness["start_args"], harness["kind"])
    for name, role in config["roles"].items():
        fields(role, {"definition", "harness", "skills"}, f"roles.{name}", {"definition", "harness", "skills"})
        if role["harness"] not in config["harnesses"] or any(s not in config["skills"] for s in role["skills"]):
            fail(f"roles.{name}: invalid Harness or Skill reference")
    if "orchestrator" not in config["roles"]["manager"]["skills"]:
        fail("manager requires the orchestrator Skill")
    workers = [worker] if workers is None else sorted(set(workers))
    if not workers or any(r == "manager" or r not in config["roles"] for r in workers):
        fail("workers: must reference configured worker roles")
    if any("development" not in config["roles"][r]["skills"] for r in workers):
        fail("worker requires the development Skill")
    role_names = ["manager"] + workers
    for name, skill in config["skills"].items():
        fields(skill, {"directory"}, f"skills.{name}", {"directory"})
    if os.environ.get("HERDR_ENV") != "1":
        fail("required capability: run the supervisor inside Herdr (HERDR_ENV=1)")
    selected = {r: config["harnesses"][config["roles"][r]["harness"]] for r in role_names}
    for executable in {"herdr", "git"} | {h["kind"] for h in selected.values()}:
        if not shutil.which(executable):
            fail(f"required executable unavailable: {executable}")

    dependencies, role_inputs, dependency_bytes = [], {}, {}

    def dependency(path, category):
        path = path.resolve()
        for owned_root in {repo, registered_repo}:
            if inside(path, owned_root):
                ref = path.relative_to(owned_root).as_posix()
                if not any(under(ref, prefix) for prefix in config["policies"]["allowed_paths"]):
                    fail(f"{category}: dependency is outside effective allowed_paths")
        if path not in dependency_bytes:
            try:
                dependency_bytes[path] = path.read_bytes()
            except OSError:
                fail(f"required dependency unreadable: {path}")
        raw = dependency_bytes[path]
        entry = {"category": category, "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
        if entry not in dependencies:
            dependencies.append(entry)
        return str(path)

    discovery = [Path.home() / ".claude/skills", Path.home() / ".agents/skills"]
    for role_name in role_names:
        role = config["roles"][role_name]
        refs = [dependency(member(assets, role["definition"]), "role")]
        for name in role["skills"]:
            skill = config["skills"][name]
            source = member(assets, skill["directory"], directory=True)
            for root in discovery:
                link = root / name
                if not link.is_symlink() or not link.exists() or link.resolve() != source:
                    fail(f"required Skill link missing, conflicting or broken: {link}; no automatic install")
            refs.append(dependency(member(source, "SKILL.md"), "skill"))
            manifest = member(source, "resources.json")
            dependency(manifest, "skill-manifest")
            resources = load(manifest, raw=dependency_bytes[manifest])
            fields(resources, {"required_files"}, f"skills.{name}.resources", {"required_files"})
            texts(resources["required_files"], f"skills.{name}.required_files", True)
            for ref in resources["required_files"]:
                refs.append(dependency(member(source, ref), "skill-support"))
        role_inputs[role_name] = refs
    official = [root / "herdr/SKILL.md" for root in discovery]
    if not all(p.is_file() for p in official) or official[0].resolve() != official[1].resolve():
        fail("required official Herdr Skill is missing or not shared; no automatic install")
    dependency(official[0].resolve(), "official-herdr-skill")
    if any(h["kind"] == "codex" and "--profile" in h["start_args"] for h in selected.values()):
        codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
        dependency(codex_home / "herdr.config.toml", "execution-policy")
    workflow = dependency(member(assets, config["workflow"]), "workflow")
    template = dependency(member(assets, config["template"]), "template")
    context, rules = [], []
    scopes = [(repo / relative(p)).resolve().relative_to(repo).as_posix() for p in config["project"]["scope"]]
    rule_refs = config["project"]["rules"] + config["project"].get("rule_support_files", [])
    declared_rules = {member(repo, ref) for ref in rule_refs}
    for category, refs in (("project-rule", rule_refs), ("context", config["context_refs"])):
        for ref in refs:
            target = member(repo, ref)
            canonical = target.relative_to(repo).as_posix()
            if category == "context" and not any(under(canonical, prefix) for prefix in scopes):
                fail("context: requested file is outside project.scope")
            (rules if category == "project-rule" else context).append(dependency(target, category))
    # Explicit rule support is the contract; recognize native @imports and local
    # Markdown links so a missing common dependency cannot silently pass.
    for rule in declared_rules:
        try:
            body = dependency_bytes[rule].decode("utf-8")
        except UnicodeError:
            fail("project rules must be UTF-8 text")
        imports = re.findall(r"(?m)^\s*@([^\s]+)\s*$", body)
        imports += re.findall(r"\[[^\]]*\]\(([^\s)]+\.md(?:#[^\s)]*)?)\)", body)
        for ref in imports:
            if "://" in ref:
                continue
            target = (rule.parent / ref.split("#", 1)[0]).resolve()
            if not inside(target, repo) or target not in declared_rules:
                fail("project rules: imported support must be declared in project.rule_support_files within the repository")
    # Save the resolved allowlisted configuration, never environment/auth or rule contents.
    provenance, origins = [], {}
    for name, path, layer, (_, digest) in zip(["global", "project", "run"], source_paths, layers, loaded):
        provenance.append({"layer": name, "path": str(path), "sha256": digest})
        pending = [(key, value) for key, value in layer.items() if key != "policies"]
        while pending:
            key, value = pending.pop()
            if isinstance(value, dict):
                pending.extend((key + "." + child, item) for child, item in value.items())
            else:
                origins[key] = name
    origins["policies"] = "allowed_paths: intersection; require_approval/require_review: union"
    snapshot = {"format": "m1-readonly-config-v1", "run_id": identifier(run_id, "run id"),
                "config": config, "sources": provenance, "field_sources": origins, "dependencies": dependencies,
                "baseline_commit": git(repo, "rev-parse", "HEAD"), "input_root": str(repo),
                "business_task_accepted": False}
    return {"snapshot": snapshot, "role_inputs": role_inputs, "selected": selected,
            "workflow": workflow, "template": template, "context": context, "rules": rules,
            "official_skill": str(official[0])}


def prepare(home, global_path, project_id, run_path, run_id):
    prepared = resolve_configuration(home, global_path, project_id, run_path, run_id)
    snapshot = prepared["snapshot"]
    config, repo = snapshot["config"], Path(snapshot["input_root"])
    worker, role_inputs, selected = config["worker_role"], prepared["role_inputs"], prepared["selected"]
    workflow, template, rules, context = (prepared[k] for k in ("workflow", "template", "rules", "context"))
    prompt = "\n".join([
        "执行一次受监督的只读核查。只在终端返回结果，不写文件、不启动其他 Agent。",
        "目标：" + config["objective"],
        "先逐一读取以下岗位、Skill、必需支持文件、Workflow、模板与项目规则，再读取任务输入。",
        "岗位与方法：", *role_inputs[worker], "Workflow：", workflow, "结果格式：", template,
        "项目规则：", *rules, "任务输入：", *context,
        "有效读取范围（相对项目根）：" + json.dumps(config["policies"]["allowed_paths"], ensure_ascii=False),
        "按模板给出文件位置和实际内容作为依据；缺失、冲突、审批或无法读取时报告 BLOCKED。",
        "这是只读观察结果，不表示正式 Task/Attempt 或业务交付已验收。",
    ]) + "\n"
    destination = output_path(home, Path("runs") / project_id / run_id, repo)
    if destination.exists() or destination.is_symlink():
        fail("Run output already exists; do not overwrite or redispatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    save(destination / "snapshot.json", snapshot)
    save(destination / "dispatch-input.json", {
        "supervisor_reads": role_inputs["manager"] + [prepared["official_skill"], workflow] + rules,
        "worker_role": worker, "execution": selected[worker], "cwd": str(repo),
        "prompt_file": str(destination / "prompt.txt"),
        "authorization": "Preparation and high-permission launch are not business authorization; confirm scope and handle any remaining native prompts with the user.",
    })
    with (destination / "prompt.txt").open("x", encoding="utf-8") as stream:
        stream.write(prompt)
    return {"run_directory": str(destination), "worker_role": worker,
            "execution": selected[worker], "business_task_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True, help="External state directory (never the business repository)")
    commands = parser.add_subparsers(dest="command", required=True)
    reg = commands.add_parser("register", help="Register a Git project without changing it")
    reg.add_argument("--project", type=Path, required=True)
    run = commands.add_parser("prepare", help="Resolve a new readonly Run; does not dispatch")
    run.add_argument("--global", dest="global_path", type=Path, required=True)
    run.add_argument("--project-id", required=True)
    run.add_argument("--run", type=Path, required=True)
    run.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        home = args.home.expanduser().resolve()
        if args.command == "register":
            result = register(home, args.project.expanduser().resolve())
        else:
            result = prepare(home, args.global_path.expanduser().resolve(), args.project_id,
                             args.run.expanduser().resolve(), args.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ConfigError, OSError) as exc:
        # OSError may contain raw submitted filenames; keep that diagnostic bounded.
        message = str(exc) if isinstance(exc, ConfigError) else "filesystem operation failed; nothing may be dispatched"
        print("BLOCKED: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
