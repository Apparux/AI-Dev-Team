#!/usr/bin/env python3
"""Identified rehearsal and authorized test-fix records. No scheduler or automatic recovery."""

import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

_spec = importlib.util.spec_from_file_location("configuration", Path(__file__).with_name("configure.py"))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)
PROTOCOL = "identified-delivery-v1"
PHASES = {"work", "verify", "review", "fix"}
TEST_FIX = "versioned-test-fix"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def require(condition, message):
    if not condition:
        c.fail(message)


def schema(value, keys, where):
    c.fields(value, set(keys.split()), where, set(keys.split()))


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, "expected a nonnegative integer")


def text(value, where):
    # Result prose and source-code argv are not configuration credentials.
    require(isinstance(value, str) and value.strip() and not any(ord(ch) < 32 and ch != '\n' for ch in value),
            where + ": expected nonempty text")
    return value


def strings(value, where, nonempty=False):
    require(isinstance(value, list) and (value or not nonempty), where + ": expected a list")
    for item in value:
        text(item, where)


def now():
    return datetime.now(timezone.utc).isoformat()


def path_in(value, root):
    path = Path(c.text(value, "path"))
    require(path.is_absolute() and path == path.resolve() and c.inside(path, root),
            "path must be canonical and inside its authorized root")
    return path


def file_ref(path):
    require(path.is_file() and path == path.resolve(), "evidence must be a regular, canonical file")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def check_ref(ref, root):
    schema(ref, "path sha256", "file reference")
    path = path_in(ref["path"], root)
    require(ref == file_ref(path), "file fingerprint mismatch: " + str(path))
    return path


def sync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic(path, value, exclusive=True):
    require(path.parent == path.parent.resolve(), "record parent cannot be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temporary, path)  # Publish complete bytes without replacing another Attempt's result.
        else:
            require(not path.is_symlink(), "snapshot cannot be a symlink")
            os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root, shared=False):
    path = root / ".state.lock"
    require(path.is_file() and not path.is_symlink(), "Run ownership is uninitialized or ambiguous")
    with path.open("rb") as stream:
        try:
            fcntl.flock(stream, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError:
            c.fail("another supported operation holds the Run lock; no takeover")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def counters(state):
    return {key: task["repair_count"] for key, task in state["tasks"].items()}


def commit(root, before, after, actor, action, reason, fix_task=None):
    c.text(reason, "event reason")
    after["revision"] = before["revision"] + 1 if before else 1
    previous = after.pop("event_hash", None)
    event = {"revision": after["revision"], "previous_event": previous,
             "actor": actor, "action": action, "reason": reason, "at": now(),
             "before_hash": digest({k: v for k, v in before.items() if k != "event_hash"}) if before else None,
             "after_hash": digest(after), "before_status": before["status"] if before else None,
             "after_status": after["status"], "repair_counts": counters(after), "fix_task": fix_task}
    event["hash"] = digest(event)
    events = root / "events.jsonl"
    require(not events.is_symlink(), "events cannot be a symlink")
    with events.open("ab") as stream:
        stream.write(encoded(event) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    after["event_hash"] = event["hash"]
    atomic(root / "state.json", after, exclusive=before is None)


def read_state(root):
    state = c.load(root / "state.json")
    schema(state, "protocol run_id run_ref owner revision event_hash status tasks attempts handoffs", "state")
    require(state["protocol"] == PROTOCOL, "unsupported state protocol")
    integer(state["revision"], 1)
    schema(state["owner"], "id generation", "owner")
    c.identifier(state["owner"]["id"], "owner id")
    integer(state["owner"]["generation"], 1)
    raw = (root / "events.jsonl").read_bytes()
    require(raw.endswith(b"\n"), "partial event; manual reconciliation required")
    events = [json.loads(line, object_pairs_hook=c.unique_pairs) for line in raw.splitlines()]
    require(len(events) == state["revision"], "snapshot/event revision mismatch; no automatic recovery")
    previous, last_hash, counts = None, None, {key: 0 for key in state["tasks"]}
    for revision, event in enumerate(events, 1):
        schema(event, "revision previous_event actor action reason at before_hash after_hash before_status after_status repair_counts fix_task hash", "event")
        require(event["revision"] == revision and event["previous_event"] == previous,
                "broken event sequence")
        require(event["before_hash"] == last_hash, "snapshot/event hash chain mismatch")
        require(event["hash"] == digest({k: v for k, v in event.items() if k != "hash"}), "event hash mismatch")
        if event["fix_task"] is not None:
            require(event["action"] == "dispatch" and event["fix_task"] in counts, "invalid repair event")
            counts[event["fix_task"]] += 1
        require(event["repair_counts"] == counts, "repair event counts are inconsistent")
        previous, last_hash = event["hash"], event["after_hash"]
    require(previous == state["event_hash"] and last_hash == digest({k: v for k, v in state.items() if k != "event_hash"}),
            "snapshot/event content mismatch; manual reconciliation required")
    require(counters(state) == counts, "repair snapshot counts are inconsistent")
    run = c.load(check_ref(state["run_ref"], root))
    require(run["run_id"] == state["run_id"] and run["record_root"] == str(root), "Run identity/record directory mismatch")
    check_ref(run["authorization"], root)
    for task in state["tasks"].values():
        check_ref(task["card"], root)
        integer(task["repair_count"])
        require(task["repair_count"] <= run["repair_limit"], "repair budget exceeded")
        check_version(task["version"], run, [root, Path(run["workspace"])])
        if task["report"] is not None:
            check_ref(task["report"], root / "reports")
    for approval in state["handoffs"]:
        check_ref(approval, root)
    for attempt in state["attempts"].values():
        check_ref(attempt["dispatch"], root)
        for key in ("binding", "stopped", "accepted"):
            if attempt[key] is not None:
                referenced = c.load(check_ref(attempt[key], root))
                if key in {"binding", "stopped"}:
                    check_ref(referenced["evidence"], root / "evidence")
        if attempt["accepted"] is not None:
            result = c.load(Path(attempt["accepted"]["path"]))
            for key in ("input_version", "output_version"):
                check_version(result[key], run, [root, Path(run["workspace"])])
            for check in result["checks"]:
                check_ref(check["evidence"], root)
            for finding in result["findings"]:
                check_ref(finding["evidence"], root)
    if test_fix(run):
        task = next(iter(state["tasks"].values()))
        active = state["attempts"].get(task["current"])
        phase = c.load(check_ref(active["dispatch"], root))["phase"] if active else None
        if phase not in {"work", "fix"}:
            current_version(run, task["version"])
    return state, run


def test_fix(run):
    return run.get("mode", "non-business") == TEST_FIX


def git_bytes(run, *args):
    try:
        result = subprocess.run(["git", "-C", run["workspace"], *args], capture_output=True,
                                timeout=10, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except (OSError, subprocess.TimeoutExpired):
        c.fail("Git version evidence unavailable")
    require(result.returncode == 0, "Git version evidence unavailable: " + args[0])
    return result.stdout


def changed_paths(run, before, after):
    raw = git_bytes(run, "diff", "--name-only", "--no-renames", "--ignore-submodules=none",
                    "--no-ext-diff", "--no-textconv", "-z", before, after, "--")
    return sorted(p.decode("utf-8") for p in raw.split(b"\0") if p)


def check_commit(run, head):
    require(isinstance(head, str) and len(head) == 40 and all(ch in "0123456789abcdef" for ch in head),
            "expected a full Git commit id")
    require(c.git(Path(run["workspace"]), "rev-parse", "--verify", head + "^{commit}") == head,
            "version is not a commit")
    require(c.git(Path(run["workspace"]), "merge-base", run["baseline"], head) == run["baseline"],
            "version is not a descendant of the authorized baseline")
    commits = c.git(Path(run["workspace"]), "rev-list", "--reverse", run["baseline"] + ".." + head).splitlines()
    require(not c.git(Path(run["workspace"]), "rev-list", "--min-parents=2", run["baseline"] + ".." + head),
            "test-fix delivery does not authorize merge commits")
    # Check every commit, not just the net diff: an out-of-scope edit cannot be hidden by a later revert.
    for commit_id in commits:
        paths = changed_paths(run, commit_id + "^", commit_id)
        require(set(paths) <= set(run["write_paths"]), "commit changes a path outside the test-write authorization")
        for path in paths:
            entry = c.git(Path(run["workspace"]), "ls-tree", commit_id, "--", path)
            require(entry.startswith("100644 blob ") and entry.endswith("\t" + path),
                    "test-fix delivery only modifies existing regular test files")


def current_version(run, value):
    require(c.git(Path(run["workspace"]), "rev-parse", "HEAD") == value["head_commit"],
            "workspace HEAD differs from the pinned stage version")


def test_authorization(grant, request, cards, workspace):
    schema(grant, "decision mode run_id task_id repository workspace branch baseline record_root "
           "attempt_result_write business_code_write test_code_write local_commit employee_sessions evidence_write "
           "original_workspace_write remote_write network_access write_paths validation_argv validation_inputs reason", "test-fix authorization")
    require(grant["mode"] == TEST_FIX and len(cards) == 1 and grant["task_id"] in cards,
            "test-fix authorization requires exactly one matching Task")
    for key in ("test_code_write", "local_commit", "employee_sessions", "evidence_write"):
        require(grant[key] is True, "explicit authorization is required: " + key)
    for key in ("original_workspace_write", "remote_write", "network_access"):
        require(grant[key] is False, "test-fix delivery forbids: " + key)
    c.texts(grant["write_paths"], "test write paths", True)
    card = cards[grant["task_id"]]
    require(not card["depends_on"], "test-fix mode supports one independent Task")
    scopes = [(workspace / c.relative(p)).resolve().relative_to(workspace).as_posix() for p in card["scope"]]
    for ref in grant["write_paths"]:
        path = workspace / c.relative(ref)
        require(path == path.resolve() and path.is_file() and ref == path.relative_to(workspace).as_posix(),
                "test write path must name an existing canonical file")
        require(any(c.under(ref, scope) for scope in scopes), "test write path is outside Task scope")
        entry = c.git(workspace, "ls-tree", request["baseline"], "--", ref)
        require(entry.startswith("100644 blob ") and entry.endswith("\t" + ref),
                "test write path must be a tracked regular file at the baseline")
    commands = grant["validation_argv"]
    require(isinstance(commands, list) and commands, "approved validation argv is required")
    for argv in commands:
        strings(argv, "validation argv", True)
    require(isinstance(grant["validation_inputs"], list), "validation inputs must be file references")
    for ref in grant["validation_inputs"]:
        check_ref(ref, Path(grant["record_root"]) / "inputs")
    text(grant["reason"], "authorization reason")


def workspace_owner_path(run):
    directory = Path(c.git(Path(run["workspace"]), "rev-parse", "--absolute-git-dir")).resolve()
    require(directory != Path(c.git(Path(run["repository"]), "rev-parse", "--absolute-git-dir")).resolve(),
            "Run requires its own worktree administrative directory")
    return directory / "ai-dev-team-owner.json"


def workspace_check(run, require_claim=True):
    repo, workspace = Path(run["repository"]), Path(run["workspace"])
    common = lambda p: c.resolve(c.git(p, "rev-parse", "--git-common-dir"), p)
    require(repo != workspace and common(repo) == common(workspace), "Run worktree repository ownership mismatch")
    require(Path(c.git(workspace, "rev-parse", "--show-toplevel")).resolve() == workspace, "workspace root mismatch")
    require(c.git(workspace, "symbolic-ref", "--short", "HEAD") == run["branch"], "Run branch mismatch")
    for path in (repo, workspace):
        head = c.git(path, "rev-parse", "HEAD")
        if path == workspace and test_fix(run):
            check_commit(run, head)
        else:
            require(head == run["baseline"], "original workspace or rehearsal baseline changed")
        require(not c.git(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"),
                "repository has uncommitted changes")
    for entry in run["prepared"]["snapshot"]["dependencies"]:
        path = Path(entry["path"])
        if test_fix(run) and entry["category"] == "context" and c.inside(path, workspace):
            relative = path.relative_to(workspace).as_posix()
            actual = hashlib.sha256(git_bytes(run, "cat-file", "blob", run["baseline"] + ":" + relative)).hexdigest()
        else:
            actual = file_ref(path)["sha256"]
        require(actual == entry["sha256"], "input/rule changed; block and reconcile")
    if test_fix(run):
        for ref in run["validation_inputs"]:
            check_ref(ref, Path(run["record_root"]) / "inputs")
    if require_claim:
        expected = workspace_owner_path(run)
        require(run["workspace_claim"]["path"] == str(expected), "workspace ownership location mismatch")
        claim = c.load(check_ref(run["workspace_claim"], expected.parent))
        require(claim == {k: run[k] for k in ("run_id", "record_root", "workspace", "branch")},
                "workspace is owned by another Run")


def version(run, artifacts):
    return {"base_commit": run["baseline"], "head_commit": run["baseline"], "artifacts": artifacts}


def check_version(value, run, roots):
    schema(value, "base_commit head_commit artifacts", "version")
    require(value["base_commit"] == run["baseline"], "wrong Git baseline")
    if test_fix(run):
        check_commit(run, value["head_commit"])
    else:
        require(value["head_commit"] == run["baseline"], "wrong Git version")
    require(isinstance(value["artifacts"], list), "version.artifacts must be a list")
    require(not test_fix(run) or not value["artifacts"], "test-fix deliverables are pinned Git versions, not mutable artifacts")
    seen = set()
    for ref in value["artifacts"]:
        require(isinstance(ref, dict) and isinstance(ref.get("path"), str), "invalid artifact reference")
        path = Path(ref["path"])
        require(any(c.inside(path, root) for root in roots) and ref["path"] not in seen, "artifact outside scope or duplicated")
        check_ref(ref, next(root for root in roots if c.inside(path, root)))
        seen.add(ref["path"])


def validate_tasks(cards, run_id, workspace, config):
    require(isinstance(cards, list) and cards, "at least one Task is required")
    by_id = {}
    for card in cards:
        schema(card, "run_id task_id owner_role objective scope depends_on workspace context_refs acceptance required_stages", "Task")
        task_id = c.identifier(card["task_id"], "task id")
        require(task_id not in by_id and card["run_id"] == run_id and card["workspace"] == str(workspace), "Task identity/workspace mismatch")
        c.text(card["objective"], "objective")
        for key in ("scope", "context_refs", "acceptance", "depends_on"):
            c.texts(card[key], key, key != "depends_on")
        project_scopes = [(workspace / c.relative(p)).resolve().relative_to(workspace).as_posix()
                          for p in config["project"]["scope"]]
        task_scopes = []
        for ref in card["scope"]:
            target = (workspace / c.relative(ref)).resolve()
            require(c.inside(target, workspace) and (target.is_file() or target.is_dir()), "Task scope is missing or escapes the workspace")
            canonical = target.relative_to(workspace).as_posix()
            require(any(c.under(canonical, p) for p in config["policies"]["allowed_paths"]), "Task scope outside allowed paths")
            require(any(c.under(canonical, p) for p in project_scopes), "Task scope outside project scope")
            task_scopes.append(canonical)
        for ref in card["context_refs"]:
            canonical = c.member(workspace, ref).relative_to(workspace).as_posix()
            require(any(c.under(canonical, p) for p in task_scopes), "Task input outside its own scope")
        stages = card["required_stages"]
        c.fields(stages, {"work", "verify", "review"}, "required stages", {"work", "verify"})
        require(card["owner_role"] == stages["work"], "Task owner must own work/fix")
        require(not config["policies"]["require_review"] or "review" in stages, "required Review cannot be omitted")
        require(all(role != "manager" and role in config["roles"] for role in stages.values()), "unconfigured stage role")
        by_id[task_id] = card
    visited, visiting = set(), set()
    def visit(task_id):
        require(task_id in by_id, "missing Task dependency")
        require(task_id not in visiting, "cyclic Task dependency")
        if task_id not in visited:
            visiting.add(task_id)
            for dependency in by_id[task_id]["depends_on"]:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)
    for task_id in by_id:
        visit(task_id)
    return by_id


def initialize(root, request):
    keys = set("run_id project_id repository workspace branch baseline owner_id configuration authorization repair_limit tasks".split())
    c.fields(request, keys | {"mode"}, "initialize", keys)
    mode = request.get("mode", "non-business")
    require(mode in {"non-business", TEST_FIX}, "unsupported delivery mode")
    for key in ("run_id", "project_id", "owner_id"):
        c.identifier(request[key], key)
    integer(request["repair_limit"])
    schema(request["configuration"], "home global run", "configuration inputs")
    require(root.is_dir() and root == root.resolve(), "create the approved external Run directory first")
    repo, workspace = (Path(request[k]).resolve() for k in ("repository", "workspace"))
    require(not c.inside(root, repo) and not c.inside(root, workspace), "records must be outside both workspaces")
    grant = c.load(check_ref(request["authorization"], root))
    require(grant.get("decision") == "approved" and grant.get("business_code_write") is False,
            "explicit authorization excluding production code changes is required")
    require(grant.get("mode", "non-business") == mode, "authorization delivery mode mismatch")
    for key in ("run_id", "repository", "workspace", "branch", "baseline"):
        require(grant.get(key) == request[key], "authorization target mismatch: " + key)
    require(grant.get("record_root") == str(root) and grant.get("attempt_result_write") is True,
            "Attempt result write scope is not authorized")
    require(isinstance(request["tasks"], list), "tasks must be a list")
    roles = []
    for card in request["tasks"]:
        require(isinstance(card, dict) and isinstance(card.get("required_stages"), dict), "invalid Task stages")
        roles.extend(card["required_stages"].values())
    cfg = request["configuration"]
    prepared = c.resolve_configuration(Path(cfg["home"]).resolve(), Path(cfg["global"]).resolve(),
                                       request["project_id"], Path(cfg["run"]).resolve(), request["run_id"], workspace, roles)
    require(prepared["snapshot"]["config"]["project"]["repository"] == str(repo), "registered repository mismatch")
    config = prepared["snapshot"]["config"]
    require(config["workflow"] == "workflows/identified-delivery.md" and config["template"] == "templates/identified-result.json"
            and c.load(Path(prepared["template"])).get("protocol") == PROTOCOL,
            "initialize requires the identified workflow and result protocol, not readonly observation assets")
    prepared["snapshot"]["format"] = "m1-identified-config-v1"
    cards = validate_tasks(request["tasks"], request["run_id"], workspace, prepared["snapshot"]["config"])
    run = {key: request[key] for key in ("run_id", "project_id", "repository", "workspace", "branch", "baseline", "authorization", "repair_limit")}
    run.update(protocol=PROTOCOL, mode=mode, record_root=str(root), prepared=prepared)
    if test_fix(run):
        test_authorization(grant, request, cards, workspace)
        run.update(write_paths=grant["write_paths"], validation_argv=grant["validation_argv"], validation_inputs=grant["validation_inputs"])
        require(c.git(workspace, "rev-parse", "HEAD") == run["baseline"], "test-fix worktree must start at the baseline")
        dependencies = prepared["snapshot"]["dependencies"]
        context_paths = {str(c.member(workspace, ref)) for card in cards.values() for ref in card["context_refs"]}
        context_paths.update(entry["path"] for entry in dependencies if entry["category"] == "context")
        # Pin every Task input to Git bytes, not checkout bytes (which may use CRLF or filters).
        for path in sorted(context_paths):
            relative = Path(path).relative_to(workspace).as_posix()
            sha = hashlib.sha256(git_bytes(run, "cat-file", "blob", run["baseline"] + ":" + relative)).hexdigest()
            existing = next((entry for entry in dependencies if entry["category"] == "context" and entry["path"] == path), None)
            if existing is None:
                dependencies.append({"category": "context", "path": path, "sha256": sha})
            else:
                existing["sha256"] = sha
        for entry in dependencies:
            require(entry["category"] == "context" or Path(entry["path"]) not in {workspace / p for p in run["write_paths"]},
                    "test write paths cannot overlap rules or execution assets")
    run["rules_digest"] = digest(prepared["snapshot"]["dependencies"])
    workspace_check(run, require_claim=False)
    claim_path = workspace_owner_path(run)
    require(not claim_path.exists() and not claim_path.is_symlink(), "workspace already has a Run owner; no takeover")
    require(not any((root / p).exists() or (root / p).is_symlink() for p in (".state.lock", "run.yaml", "state.json", "events.jsonl", "tasks", "reports")),
            "Run already exists or initialization is incomplete; do not take over")
    fd = os.open(str(root / ".state.lock"), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with locked(root):
        atomic(claim_path, {k: run[k] for k in ("run_id", "record_root", "workspace", "branch")})
        run["workspace_claim"] = file_ref(claim_path)
        atomic(root / "run.yaml", run)
        state = {"protocol": PROTOCOL, "run_id": request["run_id"], "run_ref": file_ref(root / "run.yaml"),
                 "owner": {"id": request["owner_id"], "generation": 1}, "revision": 0,
                 "status": "active", "tasks": {}, "attempts": {}, "handoffs": []}
        for task_id, card in cards.items():
            directory = root / "tasks" / task_id
            directory.mkdir(parents=True)
            atomic(directory / "task.yaml", card)
            state["tasks"][task_id] = {"card": file_ref(directory / "task.yaml"), "status": "pending",
                "repair_count": 0, "current": None, "satisfied": {}, "dependencies": {}, "report": None, "last_result": None,
                "version": version(run, [] if test_fix(run) else [file_ref(c.member(workspace, p)) for p in card["context_refs"]])}
        (root / "reports").mkdir()
        commit(root, None, state, state["owner"], "initialize", "approved " + mode + " delivery")
    return state


def authorize(state, owner, generation, revision):
    require(state["owner"] == {"id": owner, "generation": generation}, "supervisor identity/generation mismatch; no takeover")
    require(state["revision"] == revision, "stale supervisor revision")


def current(state, task_id, attempt_id):
    require(task_id in state["tasks"], "unknown Task")
    key = task_id + "/" + attempt_id
    require(key in state["attempts"] and state["tasks"][task_id]["current"] == key, "old, duplicate or noncurrent Attempt")
    return state["tasks"][task_id], state["attempts"][key]


def dispatch(root, state, run, request):
    schema(request, "task_id attempt_id phase executor_id", "dispatch")
    for key in ("task_id", "attempt_id", "executor_id"):
        c.identifier(request[key], key)
    require(state["status"] == "active", "Run is not active")
    require(request["task_id"] in state["tasks"], "unknown Task")
    require(not any(a["stopped"] is None for a in state["attempts"].values()), "workspace writer is still active or unknown")
    task = state["tasks"][request["task_id"]]
    require(task["current"] is None, "current Attempt must be reconciled before another dispatch")
    card = c.load(check_ref(task["card"], root))
    expected = {"pending": "work", "reported": "verify", "verifying": "review", "needs_fix": "fix"}.get(task["status"])
    phase = request["phase"]
    require(phase in PHASES and phase == expected, "illegal phase transition")
    require(phase != "review" or "review" in card["required_stages"], "Review is not a required stage")
    dependency_versions, dependency_results = {}, {}
    for dependency in card["depends_on"]:
        upstream = state["tasks"][dependency]
        require(upstream["status"] == "completed", "upstream Task is not completed")
        check_version(upstream["version"], run, [root])
        dependency_versions[dependency] = digest(upstream["version"])
        dependency_results[dependency] = {"version": upstream["version"], "report": upstream["report"],
            "work_result": state["attempts"][upstream["satisfied"]["work"]]["accepted"]}
    require(not task["dependencies"] or task["dependencies"] == dependency_versions, "upstream version changed")
    task["dependencies"] = dependency_versions
    if phase == "fix":
        require(task["repair_count"] < run["repair_limit"], "repair limit reached; user decision required")
        task["repair_count"] += 1
    role = card["owner_role"] if phase == "fix" else card["required_stages"][phase]
    harness = run["prepared"]["selected"][role]
    require(not (harness["kind"] == "codex" and "--profile" in harness["start_args"]), "readonly profile cannot write Attempt results")
    key = request["task_id"] + "/" + request["attempt_id"]
    require(key not in state["attempts"], "Attempt identifiers cannot be reused")
    directory = root / "tasks" / request["task_id"] / "attempts" / request["attempt_id"]
    require(not directory.exists() and not directory.is_symlink(), "Attempt path already exists")
    check_version(task["version"], run, [root, Path(run["workspace"])])
    if test_fix(run):
        current_version(run, task["version"])
    dispatch_record = {**request, "protocol": PROTOCOL, "mode": run.get("mode", "non-business"),
        "run_id": state["run_id"], "role": role,
        "workspace": run["workspace"], "cwd": str(directory), "result_path": str(directory / "result.yaml"),
        "execution": harness, "input_version": copy.deepcopy(task["version"]), "rules_digest": run["rules_digest"],
        "authorization": run["authorization"], "task_card": task["card"],
        "required_reads": run["prepared"]["role_inputs"][role] + [run["prepared"]["workflow"], run["prepared"]["template"]] + run["prepared"]["rules"],
        "work_result": state["attempts"][task["satisfied"]["work"]]["accepted"] if "work" in task["satisfied"] else None,
        "failure_result": task["last_result"] if phase == "fix" else None, "dependency_results": dependency_results,
        "intent": "reserved; bind actual execution before single prompt; no automatic redispatch"}
    directory.mkdir(parents=True)
    for sub in ("artifacts", "evidence"):
        (directory / sub).mkdir()
    atomic(directory / "dispatch.yaml", dispatch_record)
    state["attempts"][key] = {"dispatch": file_ref(directory / "dispatch.yaml"), "binding": None, "stopped": None, "accepted": None}
    task["current"] = key
    task["status"] = {"work": "running", "fix": "running", "verify": "verifying", "review": "reviewing"}[phase]
    return {"dispatch": dispatch_record}, request["task_id"] if phase == "fix" else None


def bind_or_stop(root, state, run, request, stopping=False):
    schema(request, "task_id attempt_id executor pane_id session_id evidence", "execution observation")
    task, attempt = current(state, request["task_id"], request["attempt_id"])
    record = c.load(check_ref(attempt["dispatch"], root))
    require(request["executor"] == record["executor_id"], "observed executor mismatch")
    for key in ("pane_id", "session_id"):
        c.text(request[key], key)
    check_ref(request["evidence"], root / "evidence")
    observation = {"executor_id": request["executor"], "pane_id": request["pane_id"],
        "session_id": request["session_id"], "kind": record["execution"]["kind"]}
    field = "stopped" if stopping else "binding"
    require(attempt[field] is None, "execution observation is already sealed")
    if test_fix(run) and not stopping:
        current_version(run, record["input_version"])
    if stopping:
        require(attempt["binding"] is not None, "cannot confirm stopping an unbound executor")
        binding = c.load(check_ref(attempt["binding"], root))
        require(binding["executor"] == observation, "stopped identity differs from bound execution")
    elif record["phase"] in {"verify", "review"}:
        producer = state["attempts"].get(task["satisfied"].get("work"))
        require(producer is not None, "independent check requires accepted work")
        identity = c.load(check_ref(producer["binding"], root))["executor"]
        require(all(observation[k] != identity[k] for k in ("executor_id", "session_id")), "verification must use an independent execution")
    path = Path(record["cwd"]) / (field + ".json")
    atomic(path, {"executor": observation, "evidence": request["evidence"], "at": now(), "stopped": stopping})
    attempt[field] = file_ref(path)
    return {field: attempt[field]}, None


def validate_result(root, state, run, result):
    schema(result, "protocol run_id task_id attempt_id phase role executor rules_digest input_version output_version outcome summary changes checks risks handoff_refs findings", "result")
    require(result["protocol"] == PROTOCOL and result["run_id"] == state["run_id"], "result protocol/Run mismatch")
    task, attempt = current(state, result["task_id"], result["attempt_id"])
    record = c.load(check_ref(attempt["dispatch"], root))
    for key in ("run_id", "task_id", "attempt_id", "phase", "role", "rules_digest", "input_version"):
        require(result[key] == record[key], "result identity/phase/version mismatch: " + key)
    require(attempt["binding"] is not None, "execution identity has not been bound")
    require(result["executor"] == c.load(check_ref(attempt["binding"], root))["executor"], "result executor mismatch")
    require(result["outcome"] in {"PASS", "BLOCKED", "FAIL"}, "invalid result outcome")
    text(result["summary"], "result summary")
    for key in ("risks", "handoff_refs"):
        strings(result[key], key)
    directory = Path(record["cwd"])
    check_version(result["input_version"], run, [root, Path(run["workspace"])])
    if record["phase"] in {"verify", "review"}:
        require(result["output_version"] == result["input_version"], "verification cannot replace the deliverable version")
    else:
        check_version(result["output_version"], run, [directory / "artifacts"])
        if not test_fix(run):
            require(result["outcome"] != "PASS" or result["output_version"]["artifacts"], "PASS requires a non-business deliverable")
    schema(result["changes"], "code artifacts", "changes")
    if test_fix(run):
        current_version(run, result["output_version"])
        before, after = (result[key]["head_commit"] for key in ("input_version", "output_version"))
        require(c.git(Path(run["workspace"]), "merge-base", before, after) == before,
                "output commit must descend from the dispatched input")
        code_changes = changed_paths(run, before, after)
        require(result["changes"]["code"] == code_changes, "reported code changes differ from the actual commit diff")
        if record["phase"] in {"work", "fix"} and result["outcome"] == "PASS":
            require(code_changes, "PASS requires an actual test-file change and commit")
    else:
        require(result["changes"]["code"] == [], "this rehearsal does not authorize code changes")
    expected_changes = [r["path"] for r in result["output_version"]["artifacts"]] if record["phase"] in {"work", "fix"} else []
    require(result["changes"]["artifacts"] == expected_changes, "reported changes do not match the deliverable")
    require(isinstance(result["checks"], list), "checks must be a list")
    require(result["outcome"] != "PASS" or result["checks"], "PASS without check evidence is forbidden")
    for check in result["checks"]:
        version_field = " head_commit" if test_fix(run) else ""
        schema(check, "argv cwd exit_code evidence" + version_field, "check")
        strings(check["argv"], "check argv", True)
        expected_cwd = run["workspace"] if test_fix(run) else str(directory)
        require(check["cwd"] == expected_cwd, "check cwd is outside its authorized workspace")
        if test_fix(run):
            require(check["argv"] in run["validation_argv"], "check is not an approved validation command")
            require(check["head_commit"] == result["output_version"]["head_commit"], "check evidence is for a different commit")
        require(type(check["exit_code"]) is int, "invalid check exit code")
        evidence = c.load(check_ref(check["evidence"], directory / "evidence"))
        schema(evidence, "argv cwd exit_code stdout stderr" + version_field, "check evidence")
        fields = ("argv", "cwd", "exit_code", "head_commit") if test_fix(run) else ("argv", "cwd", "exit_code")
        require(all(evidence[k] == check[k] for k in fields), "check evidence differs from result")
        require(isinstance(evidence["stdout"], str) and isinstance(evidence["stderr"], str), "check output must be text")
        require(result["outcome"] != "PASS" or check["exit_code"] == 0, "failed check cannot support PASS")
    require(isinstance(result["findings"], list), "findings must be a list")
    finding_ids = set()
    for finding in result["findings"]:
        schema(finding, "id location version severity evidence blocking disposition", "finding")
        c.identifier(finding["id"], "finding id")
        require(finding["id"] not in finding_ids, "duplicate finding id")
        finding_ids.add(finding["id"])
        for key in ("location", "severity", "disposition"):
            text(finding[key], "finding." + key)
        check_ref(finding["evidence"], directory / "evidence")
        require(record["phase"] == "review", "findings are only accepted from Review")
        require(finding["version"] == digest(result["input_version"]), "finding version mismatch")
        require(type(finding["blocking"]) is bool, "finding.blocking must be boolean")
        require(result["outcome"] != "PASS" or not finding["blocking"], "blocking finding cannot support PASS")
    return task, attempt, record


def publish(root, result):
    with locked(root, shared=True):
        state, run = read_state(root)
        workspace_check(run)
        task, attempt, record = validate_result(root, state, run, result)
        require(attempt["stopped"] is None and attempt["accepted"] is None, "execution is stopped or already accepted")
        path = Path(record["result_path"])
        atomic(path, result)
        return {"published": file_ref(path), "state_advanced": False}


def accept(root, state, run, request):
    schema(request, "task_id attempt_id", "accept")
    task, attempt = current(state, request["task_id"], request["attempt_id"])
    record = c.load(check_ref(attempt["dispatch"], root))
    require(attempt["stopped"] is not None, "writer has not been confirmed stopped")
    require(attempt["accepted"] is None, "duplicate result acceptance")
    path = Path(record["result_path"])
    result = c.load(path)
    require(isinstance(result, dict), "result must be a mapping")
    require(result.get("task_id") == request["task_id"] and result.get("attempt_id") == request["attempt_id"],
            "result identity differs from the accept target")
    validated_task, validated_attempt, _ = validate_result(root, state, run, result)
    require(validated_task is task and validated_attempt is attempt, "result cannot be accepted for another execution")
    attempt["accepted"] = file_ref(path)
    task["last_result"] = attempt["accepted"]
    task["current"] = None
    phase, outcome = record["phase"], result["outcome"]
    if outcome == "PASS":
        if phase in {"work", "fix"}:
            task["satisfied"] = {"work": request["task_id"] + "/" + request["attempt_id"]}
            task["version"] = result["output_version"]
            task["status"] = "reported"
        else:
            task["satisfied"][phase] = request["task_id"] + "/" + request["attempt_id"]
            task["status"] = "verifying" if phase == "verify" else "reviewing"
    elif outcome == "BLOCKED":
        if test_fix(run) and phase in {"work", "fix"}:
            task["version"] = result["output_version"]
            task["satisfied"] = {}
        task["status"], state["status"] = "blocked", "paused"
    else:
        task["status"] = "needs_fix"
        if phase in {"work", "fix"} and (test_fix(run) or result["output_version"]["artifacts"]):
            task["version"] = result["output_version"]
            if test_fix(run):
                task["satisfied"] = {}
        if task["repair_count"] >= run["repair_limit"]:
            state["status"] = "paused"
    return {"task_status": task["status"], "run_status": state["status"]}, None


def finish(root, state, run, request):
    schema(request, "task_id", "finish")
    require(state["status"] == "active", "Run is not active")
    require(request["task_id"] in state["tasks"], "unknown Task")
    require(not any(a["stopped"] is None for a in state["attempts"].values()), "unfinished writer prevents completion")
    task = state["tasks"][request["task_id"]]
    card = c.load(check_ref(task["card"], root))
    require(task["status"] in {"verifying", "reviewing"} and task["current"] is None, "illegal completed transition")
    require(set(card["required_stages"]) <= set(task["satisfied"]), "required stage evidence is missing")
    check_version(task["version"], run, [root])
    if test_fix(run):
        current_version(run, task["version"])
        require(changed_paths(run, run["baseline"], task["version"]["head_commit"]), "final delivery has no test-file change")
    results = {}
    for phase in card["required_stages"]:
        attempt = state["attempts"][task["satisfied"][phase]]
        result = c.load(check_ref(attempt["accepted"], root))
        require(result["outcome"] == "PASS" and result["output_version"] == task["version"], "stage evidence does not cover final version")
        record = c.load(check_ref(attempt["dispatch"], root))
        for check in result["checks"]:
            check_ref(check["evidence"], Path(record["cwd"]) / "evidence")
            if test_fix(run):
                require(check["head_commit"] == task["version"]["head_commit"], "final check is stale")
        results[phase] = attempt["accepted"]
    for dependency, pinned in task["dependencies"].items():
        require(state["tasks"][dependency]["status"] == "completed" and digest(state["tasks"][dependency]["version"]) == pinned, "dependency is no longer completed at the pinned version")
        check_version(state["tasks"][dependency]["version"], run, [root])
    task["status"] = "completed"
    path = root / "reports" / (request["task_id"] + ".json")
    atomic(path, {"run_id": state["run_id"], "task_id": request["task_id"], "outcome": "PASS",
        "business_task_accepted": test_fix(run), "mode": run.get("mode", "non-business"),
        "scope": "versioned test-fix; production implementation unchanged" if test_fix(run) else "non-business delivery rehearsal only",
        "production_code_changed": False,
        "changed_paths": changed_paths(run, run["baseline"], task["version"]["head_commit"]) if test_fix(run) else [],
        "version": task["version"], "stages": results, "branch": run["branch"],
        "workspace": run["workspace"], "original_workspace": run["repository"], "at": now(),
        "limitations": ["Cooperative state protection, not a Shell sandbox", "Records reread, not full interruption recovery"]})
    task["report"] = file_ref(path)
    if all(t["status"] == "completed" for t in state["tasks"].values()):
        state["status"] = "completed"
    return {"report": file_ref(path), "run_status": state["status"]}, None


def handoff(root, state, run, request):
    schema(request, "new_owner_id approval", "handoff")
    c.identifier(request["new_owner_id"], "new owner")
    require(request["new_owner_id"] != state["owner"]["id"], "handoff requires a new supervisor identity")
    require(not any(t["current"] for t in state["tasks"].values()) and not any(a["stopped"] is None for a in state["attempts"].values()), "pending execution prevents this minimal handoff")
    approval = c.load(check_ref(request["approval"], root))
    schema(approval, "action run_id old_owner new_owner_id decision pending_attempts reason", "handoff approval")
    require(approval["action"] == "handoff" and approval["run_id"] == state["run_id"] and approval["old_owner"] == state["owner"] and approval["new_owner_id"] == request["new_owner_id"] and approval["decision"] == "approved" and approval["pending_attempts"] == [], "handoff requires a matching explicit decision and cleared executions")
    state["handoffs"].append(request["approval"])
    state["owner"] = {"id": request["new_owner_id"], "generation": state["owner"]["generation"] + 1}
    return {"owner": state["owner"], "approval": request["approval"]}, None


def mutate(root, action, request, owner, generation, revision, reason):
    c.text(reason, "event reason")
    with locked(root):
        before, run = read_state(root)
        authorize(before, owner, generation, revision)
        workspace_check(run)
        state = copy.deepcopy(before)
        if action in {"bind", "stopped"}:
            result, fix_task = bind_or_stop(root, state, run, request, action == "stopped")
        else:
            result, fix_task = {"dispatch": dispatch, "accept": accept, "finish": finish, "handoff": handoff}[action](root, state, run, request)
        commit(root, before, state, before["owner"], action, reason, fix_task)
        return {**result, "revision": state["revision"], "owner": state["owner"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("action", choices=["initialize", "inspect", "publish", "dispatch", "bind", "stopped", "accept", "finish", "handoff"])
    parser.add_argument("--request", type=Path)
    parser.add_argument("--owner")
    parser.add_argument("--generation", type=int)
    parser.add_argument("--revision", type=int)
    parser.add_argument("--reason", default="explicit supervised action")
    args = parser.parse_args()
    try:
        root = args.run_dir.expanduser().resolve()
        if args.action == "inspect":
            with locked(root, shared=True):
                state, run = read_state(root)
                workspace_check(run)
                result = {"state": state, "pending_executions": {k: v for k, v in state["attempts"].items() if v["accepted"] is None}, "automatic_resume": False}
        else:
            require(args.request is not None, "--request is required")
            request = c.load(args.request)
            if args.action == "initialize":
                result = initialize(root, request)
            elif args.action == "publish":
                result = publish(root, request)
            else:
                result = mutate(root, args.action, request, args.owner, args.generation, args.revision, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (c.ConfigError, OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, c.ConfigError) else "invalid or incomplete record/filesystem; preserve evidence and reconcile"
        print("BLOCKED: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
