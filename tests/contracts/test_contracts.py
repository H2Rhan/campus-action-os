import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


VAO_SCHEMA = load(ROOT / "schemas/v1/verified-action-object.schema.json")
GRAPH_SCHEMA = load(ROOT / "schemas/v1/action-graph.schema.json")
VALID = load(ROOT / "examples/verified-action-object/valid/examples.json")
BY_CASE = {item["case"]: item for item in VALID}


def schema_errors(schema, instance):
    return list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance))


def evidence_rules(action):
    """Rules intentionally outside JSON Schema: cross-object references and epistemic safety."""
    errors = []
    evidence = {item["evidence_id"]: item for item in action["evidence"]}
    critical = {"user_relevance", "target_population", "step", "deadline", "material", "location_or_platform", "condition", "exception"}

    def check_claim(status, ids, field, accepted=None):
        accepted = accepted or {field}
        if status == "explicit" and (not ids or not any(evidence.get(i, {}).get("field_name") in accepted for i in ids)):
            errors.append(f"explicit {field} has no matching evidence")

    check_claim(action["user_relevance"]["status"] == "relevant" and "explicit" or "inferred", action["user_relevance"]["evidence_ids"], "user_relevance", {"user_relevance", "target_population"})
    check_claim(action["target_population"]["epistemic_status"], action["target_population"]["evidence_ids"], "target_population", {"target_population", "user_relevance"})
    for step in action["steps"]:
        check_claim(step["epistemic_status"], step["evidence_ids"], "step", {"step", "material", "location_or_platform", "deadline", "exception"})
        for material in step.get("materials", []):
            check_claim(material["epistemic_status"], material["evidence_ids"], "material")
        if "location_or_platform" in step:
            claim = step["location_or_platform"]
            check_claim(claim["epistemic_status"], claim["evidence_ids"], "location_or_platform", {"location_or_platform", "material"})
    check_claim(action["deadline"]["epistemic_status"], action["deadline"]["evidence_ids"], "deadline")
    for material in action.get("materials", []):
        check_claim(material["epistemic_status"], material["evidence_ids"], "material")
    if "location_or_platform" in action:
        claim = action["location_or_platform"]
        check_claim(claim["epistemic_status"], claim["evidence_ids"], "location_or_platform")
    for condition in action["conditions"]:
        check_claim(condition["epistemic_status"], condition["evidence_ids"], "condition")
    for exception in action["exceptions"]:
        check_claim(exception["epistemic_status"], exception["evidence_ids"], "exception")
    for evidence_id in sum((x.get("evidence_ids", []) for x in [action["user_relevance"], action["target_population"], action["deadline"]]), []):
        if evidence_id not in evidence:
            errors.append(f"dangling evidence reference: {evidence_id}")
    if action["deadline"]["value"] is None and action["deadline"]["precision"] != "unknown":
        errors.append("null deadline value requires unknown precision")
    if action["deadline"]["epistemic_status"] == "conflict" and action["deadline"]["value"] is not None:
        errors.append("conflicted deadline cannot have a concrete value")
    if action["verification_status"] == "user_confirmed" and action["confidence"]["basis"] != "user_confirmed":
        errors.append("user_confirmed object must have user_confirmed confidence basis")
    if action["verification_status"] == "rejected" and action["task_status"] not in {"not_created", "cancelled"}:
        errors.append("rejected object cannot be an active task")
    return errors


def graph_rules(graph):
    errors = []
    nodes = {node["node_id"] for node in graph["nodes"]}
    edges = graph["edges"]
    for edge in edges:
        if edge["from_node_id"] not in nodes or edge["to_node_id"] not in nodes:
            errors.append("dangling graph endpoint")
        if edge["edge_type"] == "branches_to" and "condition_id" not in edge:
            errors.append("branch edge missing condition_id")
    adjacency = {node: [] for node in nodes}
    for edge in edges:
        if edge["edge_type"] in {"blocks", "requires", "branches_to", "postpones", "replaces"} and edge["from_node_id"] in nodes and edge["to_node_id"] in nodes:
            adjacency[edge["from_node_id"]].append(edge["to_node_id"])
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in adjacency[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in nodes):
        errors.append("execution dependency cycle")
    return errors


@pytest.mark.parametrize("example", VALID, ids=lambda x: x["case"])
def test_valid_examples_load_and_pass_schema_and_rules(example):
    artifact = copy.deepcopy(example)
    artifact.pop("case", None)
    assert not schema_errors(VAO_SCHEMA, artifact)
    assert not evidence_rules(artifact)


def test_schema_is_draft_2020_12_and_graph_example_is_valid():
    Draft202012Validator.check_schema(VAO_SCHEMA)
    Draft202012Validator.check_schema(GRAPH_SCHEMA)
    assert VAO_SCHEMA["$schema"].endswith("draft/2020-12/schema")
    graph = load(ROOT / "examples/action-graphs/branch-and-revision.json")
    assert not schema_errors(GRAPH_SCHEMA, graph)
    assert not graph_rules(graph)


def mutate(base, mutation):
    item = copy.deepcopy(BY_CASE[base])
    item.pop("case", None)
    if mutation == "remove_evidence":
        item["evidence"] = []
    elif mutation == "bad_relevance_enum":
        item["user_relevance"]["status"] = "maybe"
    elif mutation == "bad_boundary":
        item["deadline"]["boundary_semantics"] = "before"
    elif mutation == "confirmed_without_basis":
        item["verification_status"] = "user_confirmed"
    elif mutation == "conflict_concrete_value":
        item["deadline"]["value"] = "2026-09-25"
    return item


@pytest.mark.parametrize("case", load(ROOT / "examples/verified-action-object/invalid/cases.json"), ids=lambda x: x["name"])
def test_invalid_vao_examples_are_rejected(case):
    item = mutate(case["base"], case["mutation"])
    assert schema_errors( VAO_SCHEMA, item) or evidence_rules(item)


@pytest.mark.parametrize("case", load(ROOT / "examples/action-graphs/invalid.json"), ids=lambda x: x["name"])
def test_invalid_graph_examples_are_rejected(case):
    graph = case["graph"]
    assert not schema_errors(GRAPH_SCHEMA, graph)
    assert graph_rules(graph)
