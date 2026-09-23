import argparse
import json
import sys

from app.clarification import apply_clarification, create_session, load_session, session_to_dict
from app.catalog import parameter_label
from app.pipeline import next_clarification_prompt


def _field_label(field: str) -> str:
    if field == "target_refs":
        return "target device or inventory group"
    try:
        return parameter_label(field)
    except KeyError:
        return field.replace("_", " ")


def _print_pending(session) -> None:
    for task in session.pending_tasks:
        _print_question(task)


def _print_question(task) -> None:
    print(f"\nTask {task.intent_id}: {task.operation_id} [{task.status}]")
    if task.target_devices:
        print("  Targets: " + ", ".join(device["hostname"] for device in task.target_devices))
    field, question = next_clarification_prompt(task)
    print(f"  Required now - {_field_label(field)}: {question}")


def _print_target_matches(session) -> None:
    for task in session.plan.tasks:
        for evidence in task.target_resolution:
            labels = "; ".join(candidate["label"] for candidate in evidence["selected"])
            print(f"{task.intent_id}: '{evidence['description']}' -> {labels}")


def _interactive_loop(session, verbose: bool):
    while session.pending_tasks:
        task = session.pending_tasks[0]
        _print_question(task)
        field, _ = next_clarification_prompt(task)
        reply = input(f"\nAnswer for {_field_label(field)} (or 'quit' to keep the session): ").strip()
        if reply.lower() in {"quit", "exit", "q"}:
            break
        if not reply:
            print("No reply received; the task remains pending.")
            continue
        session = apply_clarification(session, task.intent_id, reply, verbose=verbose)
        if field == "target_refs":
            _print_target_matches(session)
        if task.intent_id not in {pending.intent_id for pending in session.pending_tasks}:
            print(f"Task {task.intent_id} is ready.")
        else:
            print(f"Task {task.intent_id} still needs clarification.")
    return session


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a network operation without changing devices.")
    parser.add_argument("prompt", nargs="*", help="Network operation request")
    parser.add_argument("--resume", metavar="SESSION_ID", help="Resume a saved clarification session")
    parser.add_argument("--interactive", action="store_true", help="Force terminal clarification mode")
    parser.add_argument("--no-interactive", action="store_true", help="Do not prompt for clarification")
    parser.add_argument("--verbose", action="store_true", help="Show pipeline diagnostics")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.resume:
        session = load_session(args.resume)
    else:
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            prompt = input("Network operation request: ").strip()
        if not prompt:
            raise SystemExit("A network operation request is required.")
        session = create_session(prompt, verbose=args.verbose)

    print(f"Clarification session: {session.session_id} ({session.status})")
    _print_target_matches(session)
    interactive = args.interactive or (not args.no_interactive and sys.stdin.isatty())
    if interactive and session.pending_tasks:
        session = _interactive_loop(session, args.verbose)
    elif session.pending_tasks:
        _print_pending(session)
        print("Resume with: python main.py --resume " + session.session_id + " --interactive")

    print("\nJSON SESSION:")
    print(json.dumps(session_to_dict(session), indent=2))


if __name__ == "__main__":
    main()
