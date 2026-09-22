import argparse
import json
import sys

from app.clarification import apply_clarification, create_session, load_session, session_to_dict


def _print_pending(session) -> None:
    for task in session.pending_tasks:
        print(f"\nTask {task.intent_id}: {task.operation_id} [{task.status}]")
        for index, question in enumerate(task.clarification_questions, 1):
            print(f"  {index}. {question}")


def _interactive_loop(session, verbose: bool):
    while session.pending_tasks:
        task = session.pending_tasks[0]
        _print_pending(session)
        reply = input("\nReply for this task (or 'quit' to keep the session): ").strip()
        if reply.lower() in {"quit", "exit", "q"}:
            break
        if not reply:
            print("No reply received; the task remains pending.")
            continue
        session = apply_clarification(session, task.intent_id, reply, verbose=verbose)
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
