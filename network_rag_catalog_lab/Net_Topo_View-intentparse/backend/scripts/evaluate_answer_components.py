"""Offline experiment diagnostics, never a runtime verifier or a model grader.

Only hash-pinned saved synthetic artifacts are read. Literal probes find
mentions, not entailment; semantic judgments remain attributed human reviews.
No application imports, environment loading, readers, inference or JSON repair.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
VERSION = "answer_component_coverage_v1"
HUMAN_STATUSES = {"COVERED", "OMITTED", "AMBIGUOUS", "INCORRECT", "NOT_REVIEWED",
                  "OBSERVED", "NO_VIOLATION_IDENTIFIED"}


class ArtifactError(ValueError):
    pass


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Invalid JSON constant: " + value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def pointer(value, path):
    if path == "":
        return value
    if not path.startswith("/"):
        raise ArtifactError("Expected a JSON pointer")
    for token in path[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ArtifactError("Invalid JSON pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ArtifactError("Invalid array index")
                value = value[int(token)]
            else:
                value = value[token]
        except (KeyError, IndexError, TypeError) as exc:
            raise ArtifactError("Missing JSON pointer: " + path) from exc
    return value


class SavedArtifacts:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.verified = {}
        self.cache = {}

    def read(self, ref):
        relative = Path(ref["path"])
        path = (self.root / relative).resolve()
        if (relative.is_absolute() or not path.is_relative_to(self.root)
                or path.suffix != ".json"
                or any(part.startswith(".env") for part in path.parts)):
            raise ArtifactError("Only repository-local JSON artifacts are allowed")
        if not path.is_file():
            raise ArtifactError("Missing saved artifact: " + ref["path"])
        actual = sha256(path)
        if actual != ref["sha256"]:
            raise ArtifactError("Saved artifact hash changed: " + ref["path"])
        self.verified[ref["path"]] = actual
        if path not in self.cache:
            self.cache[path] = strict_json(path.read_text(encoding="utf-8-sig"))
        return pointer(self.cache[path], ref.get("pointer", ""))


def normal(text):
    return unicodedata.normalize("NFKC", text).casefold()


def literal_pattern(literal):
    if not isinstance(literal, str) or not literal.strip():
        raise ArtifactError("Literal probes require nonempty strings")
    # Whitespace and Markdown presentation may differ. Values, spelling and
    # numeric boundaries do not; e.g. 15000 cannot stand in for 1500.
    body = r"\s+".join(re.escape(part) for part in normal(literal).split())
    return re.compile(r"(?<!\w)" + body + r"(?!\w)")


def mention_probe(text, spec):
    """A lexical diagnostic, never a complete/correct semantic verdict."""
    if not isinstance(text, str):
        return {"signal": "UNAVAILABLE", "semantic_status": "NOT_ASSESSED"}
    if spec["kind"] == "human_only":
        return {"signal": "HUMAN_REVIEW_REQUIRED", "semantic_status": "NOT_ASSESSED"}
    if spec["kind"] not in {"literal", "same_sentence"}:
        raise ArtifactError("Unknown evaluation probe")
    alternatives = spec["alternatives"]
    if not alternatives or any(not group for group in alternatives):
        raise ArtifactError("Empty probe alternatives")
    groups = [[literal_pattern(item) for item in group] for group in alternatives]
    folded = normal(text)
    global_hits = any(all(p.search(folded) for p in group) for group in groups)
    units = [text] if spec["kind"] == "literal" else re.split(r"(?<=[.!?])\s+|\n+", text)
    matches = [unit for unit in units if any(
        all(p.search(normal(unit)) for p in group) for group in groups)]
    signal = ("MENTION_CANDIDATE" if matches else "UNBOUND_MENTIONS"
              if global_hits else "REQUIRED_LITERAL_ABSENT")
    return {"signal": signal, "semantic_status": "NOT_ASSESSED",
            "matching_units": matches[:4],
            "warning": "Mentions do not establish ownership, polarity, causality or completion."}


def diagnostic_answer(raw):
    """Read an intact string for diagnosis; never construct a valid object."""
    found = re.search(r'"answer"\s*:\s*', raw)
    if not found:
        return None
    try:
        answer, _ = json.JSONDecoder().raw_decode(raw, found.end())
        return answer if isinstance(answer, str) else None
    except (ValueError, TypeError):
        return None


def records(value):
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and "kind" in value:
            yield value
        for item in value.values():
            yield from records(item)
    elif isinstance(value, list):
        for item in value:
            yield from records(item)


def source_requirement(packet, requirement):
    matches = [(r, row) for row in packet["reader_results"] for r in records(row.get("data"))
               if r["id"] == requirement["record_id"]]
    # A reused ID is not authority to choose the first source silently.
    if len(matches) != 1:
        return {"status": "MISSING_OR_AMBIGUOUS_RECORD", **requirement}
    record, envelope = matches[0]
    if envelope.get("status") != "success" or (
            isinstance(envelope.get("data"), dict) and envelope["data"].get("source_available") is False):
        return {"status": "UNAVAILABLE_SOURCE_WITH_RECORD", **requirement}
    try:
        actual = pointer(record, requirement["pointer"])
    except ArtifactError:
        return {"status": "MISSING_FIELD", **requirement}
    exact = type(actual) is type(requirement["expected"]) and actual == requirement["expected"]
    return {"status": "EXACT_OPERAND_PRESENT" if exact else "OPERAND_MISMATCH",
            **requirement, "actual": actual}


def attributed_review(artifacts, review, parsed, raw_answer):
    if review is None:
        return {"status": "NOT_REVIEWED", "authority": "No semantic decision inferred from lexical probes"}
    if review["status"] not in HUMAN_STATUSES:
        raise ArtifactError("Invalid human-review status")
    artifacts.read(review["basis"])
    if not review.get("reason"):
        raise ArtifactError("Human review needs an explanation")
    # Optional excerpts must really occur in the selected raw field, rather
    # than silently substituting an assessment for the user-facing answer.
    for excerpt in review.get("excerpts", []):
        field = raw_answer if excerpt["field"] == "answer" else json.dumps(
            (parsed or {}).get(excerpt["field"], []), ensure_ascii=False)
        if not field or excerpt["text"] not in field:
            raise ArtifactError("Review excerpt does not occur in its attributed field")
    return {**review, "authority": "Retrospective implementation-assistant review; not blinded or automated"}


def evaluate_trace(artifacts, case, row):
    trace = artifacts.read(row["trace"])
    packet_text = trace["model_messages"][-1]["content"]
    packet = strict_json(packet_text)
    raw = trace.get("raw")
    if not isinstance(raw, str):
        raise ArtifactError("Saved raw output absent")
    parse_error = None
    try:
        parsed = strict_json(raw)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("answer"), str):
            raise ValueError("No answer string in structured object")
    except ValueError as exc:
        parsed = None
        parse_error = str(exc)
    answer = parsed["answer"] if parsed else diagnostic_answer(raw)
    original_final = trace.get("final_answer")
    current_release = artifacts.read(row["current_release"]) if row.get("current_release") else None
    source_checks = [source_requirement(packet, r) for r in case["source_requirements"]]
    request_matches = packet["original_user_instruction"] == case["question"]
    request_checks = {item["id"]: item["text"] in packet["original_user_instruction"]
                      for item in packet["requested_clauses"]}
    if not case["components"] or len({c["id"] for c in case["components"]}) != len(case["components"]):
        raise ArtifactError("Component IDs must be nonempty and unique")
    known = {c["id"] for c in case["components"]}
    if set(row.get("reviews", {})) - known:
        raise ArtifactError("Review references an unknown component")
    components = []
    for component in case["components"]:
        # Preserve a reference to the old oracle; never edit or replace it.
        oracle = artifacts.read(component["oracle"])
        aux = {key: mention_probe(json.dumps(parsed.get(key, []), ensure_ascii=False), component["probe"])
               for key in ["claims", "outcome_assessments", "outcomes"]} if parsed else None
        components.append({"id": component["id"], "description": component["description"],
            "basis": component["basis"], "frozen_oracle": oracle,
            "raw_answer": mention_probe(answer, component["probe"]),
            "auxiliary": aux,
            "original_released_answer": mention_probe(original_final, component["probe"]),
            "previously_saved_current_release": mention_probe(current_release, component["probe"]),
            "human_review": attributed_review(artifacts, row.get("reviews", {}).get(component["id"]), parsed, answer)})
    forbidden = []
    forbidden_ids = {item["id"] for item in case["forbidden_inferences"]}
    if set(row.get("forbidden_reviews", {})) - forbidden_ids:
        raise ArtifactError("Review references an unknown forbidden inference")
    for item in case["forbidden_inferences"]:
        forbidden.append({"id": item["id"], "frozen_prohibition": artifacts.read(item["oracle"]),
                          "status": "HUMAN_REVIEW_REQUIRED",
                          "human_observation": attributed_review(artifacts,
                              row.get("forbidden_reviews", {}).get(item["id"]), parsed, answer),
                          "authority": "No phrase matcher certifies unsupported-inference absence"})
    return {"identity": row["identity"], "case": case["id"], "cohort": row["cohort"],
            "arm": row["arm"], "trace": row["trace"],
            "structured_output": "JSON_OBJECT_WITH_ANSWER" if parsed else "INVALID_JSON_OR_ANSWER",
            "parse_error": parse_error,
            "raw_prose_scope": "VALID_PARSED_RESPONSE" if parsed else "DIAGNOSTIC_STRING_ONLY_NOT_RELEASABLE",
            "original_question": packet["original_user_instruction"],
            "requested_clauses": packet["requested_clauses"],
            "request_coverage": {"exact_original_preserved": request_matches,
                                 "clause_text_retained": request_checks,
                                 "semantic_comprehension": "NOT_ASSESSED"},
            "source_coverage": source_checks,
            "packet_characters": len(packet_text), "packet_within_64000": len(packet_text) <= 64000,
            "original_release_exists": isinstance(original_final, str),
            "raw_prose_in_original_release": answer in original_final if answer and original_final else False,
            "raw_prose_in_saved_current_release": answer in current_release if answer and current_release else None,
            "historical_grade_unchanged": artifacts.read(row["historical_grade"]),
            "components": components, "forbidden_inferences": forbidden,
            "semantic_complete_task_score": "NOT_COMPUTED"}


def evaluate(root, registry_path):
    root = Path(root).resolve()
    path = Path(registry_path).resolve()
    if not path.is_relative_to(root):
        raise ArtifactError("Registry must be inside this repository")
    spec = strict_json(path.read_text(encoding="utf-8-sig"))
    if spec["version"] != VERSION or spec["runtime_use"] is not False:
        raise ArtifactError("Expected an evaluation-only registry")
    artifacts = SavedArtifacts(root)
    for ref in spec["frozen_artifacts"]:
        artifacts.read(ref)
    case_ids = [c["id"] for c in spec["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise ArtifactError("Duplicate case IDs")
    cases = {c["id"]: c for c in spec["cases"]}
    identities = [r["identity"] for r in spec["outputs"]]
    if len(identities) != len(set(identities)):
        raise ArtifactError("Duplicate saved-output identity")
    rows = [evaluate_trace(artifacts, cases[r["case"]], r) for r in spec["outputs"]]
    return {"version": VERSION, "registry_sha256": sha256(path),
            "method": "Offline lexical coverage signals plus attributed prior human review; not semantic certification",
            "scope": spec["scope"], "rows": rows,
            "summary": {"saved_outputs": len(rows), "distinct_registered_conditions": len(cases),
                "cohorts": dict(Counter(r["cohort"] for r in rows)),
                "json_objects_with_answer": sum(r["structured_output"] == "JSON_OBJECT_WITH_ANSWER" for r in rows),
                "component_instances": sum(len(r["components"]) for r in rows),
                "raw_answer_signals": dict(Counter(c["raw_answer"]["signal"] for r in rows for c in r["components"])),
                "human_component_statuses": dict(Counter(c["human_review"]["status"] for r in rows for c in r["components"])),
                "all_exact_requests": all(r["request_coverage"]["exact_original_preserved"] for r in rows),
                "all_checked_source_operands_present": all(s["status"] == "EXACT_OPERAND_PRESENT" for r in rows for s in r["source_coverage"]),
                "all_packets_within_limit": all(r["packet_within_64000"] for r in rows),
                "schema_validation": "NOT_REEXECUTED; use preserved provider/application diagnostics",
                "unsupported_inference_incidence": "HUMAN_REVIEW_REQUIRED_NOT_AUTOMATICALLY_COMPUTED",
                "semantic_adequacy": "NOT_AUTOMATICALLY_SCORED", "new_inference": 0, "new_retrieval": 0},
            "verified_artifacts": artifacts.verified, "runtime_integration": False, "promotion": False}


def block_external_execution(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "sqlite3.connect"}:
        raise RuntimeError("Offline evaluator forbids " + event)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output", required=True, help="A new JSON file under tmp/phase-g/iterations")
    args = parser.parse_args()
    sys.addaudithook(block_external_execution)
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / "tmp/phase-g/iterations") or output.suffix != ".json":
        raise ArtifactError("Output must be a new evaluation-audit JSON file")
    result = evaluate(ROOT, ROOT / args.registry)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
