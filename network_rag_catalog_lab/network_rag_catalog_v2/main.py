import argparse
import json
import sys

from app.clarification import apply_answer, apply_correction, confirm_session_order, create_session, load_session, session_to_dict
from app.catalog import parameter_label
from app.questions import answer_from_text


def _field_label(field: str) -> str:
    if field == "target_refs":
        return "target device or inventory group"
    try:
        return parameter_label(field)
    except KeyError:
        return field.replace("_", " ")


def _print_pending(session) -> None:
    if session.next_question:
        _print_question(session.next_question)
        print(f"  Pending questions: {len(session.pending_questions)}")


def _print_question(question, page=0, search="") -> None:
    print(f"\n{question['operation_label']} | {question['device_label']}")
    print(f"Task {question['task_id']} | Answering: {question['field_path']}")
    print(question["wording"])
    options = [(index, option) for index, option in enumerate(question["options"], 1) if search.casefold() in option["label"].casefold()]
    for index, option in options[page * 8:(page + 1) * 8]:
        print(f"  {index}. {option['label']} [{option['source_ref']} rev {option['source_revision']}]")
        print("     " + option["explanation"])
    if len(options) > 8:
        print(f"  Page {page + 1} of {(len(options) + 7) // 8}. Commands: more, filter TEXT")
    if options:
        print("Select: select 1" + (" or select 1,2" if question["multiple"] else ""))
    print("Custom answer: type a value (or value TEXT). Bare numbers are values, not option numbers.")


def _print_target_matches(session) -> None:
    for task in session.plan.tasks:
        for evidence in task.target_resolution:
            labels = "; ".join(candidate["label"] for candidate in evidence["selected"])
            print(f"{task.intent_id}: '{evidence['description']}' -> {labels}")


def _interactive_loop(session, verbose: bool):
    page, search = 0, ""
    while session.next_question or session.status == "needs_confirmation":
        question = session.next_question
        if question:
            _print_question(question, page, search)
        else:
            for issue in session.plan.issues:
                print(issue["message"])
            print("Commands: confirm order, edit TASK_ID FIELD_PATH VALUE, quit")
        reply = input("\nAnswer (or quit): ").strip()
        if reply.lower() in {"quit", "exit", "q"}:
            break
        if not reply:
            print("No reply received; the task remains pending.")
            continue
        try:
            if reply == "more" and question:
                count = sum(search.casefold() in option["label"].casefold() for option in question["options"])
                page = (page + 1) % max(1, (count + 7) // 8)
                continue
            if reply.startswith("filter "):
                search, page = reply[7:].strip(), 0
                continue
            if reply.startswith("edit "):
                _, task_id, path, value = reply.split(maxsplit=3)
                session = apply_correction(session, task_id, path, value)
            elif reply == "confirm order" and not question:
                session = confirm_session_order(session)
            elif question:
                session = apply_answer(session, answer_from_text(question, reply))
            else:
                raise ValueError("Confirm the order or correct a conflicting task.")
            for task in session.plan.tasks:
                if task.feedback:
                    print("Answer not accepted: " + task.feedback)
            print("Request status: " + session.status)
            page, search = 0, ""
        except (ValueError, KeyError) as exc:
            print(str(exc))
    return session


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a network operation without changing devices.")
    parser.add_argument("prompt", nargs="*", help="Network operation request")
    parser.add_argument("--resume", metavar="SESSION_ID", help="Resume a saved clarification session")
    parser.add_argument("--interactive", action="store_true", help="Force terminal clarification mode")
    parser.add_argument("--no-interactive", action="store_true", help="Do not prompt for clarification")
    parser.add_argument("--verbose", action="store_true", help="Show pipeline diagnostics")
    parser.add_argument("--edit", nargs=3, metavar=("TASK_ID", "FIELD_PATH", "VALUE"), help="Correct a field in a resumed session")
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

    if args.edit:
        session = apply_correction(session, *args.edit)

    print(f"Clarification session: {session.session_id} ({session.status})")
    _print_target_matches(session)
    interactive = args.interactive or (not args.no_interactive and sys.stdin.isatty())
    if interactive and (session.pending_tasks or session.status == "needs_confirmation"):
        session = _interactive_loop(session, args.verbose)
    elif session.pending_tasks:
        _print_pending(session)
        print("Resume with: python main.py --resume " + session.session_id + " --interactive")

    for issue in session.plan.issues:
        print(issue["message"])

    print("\nJSON SESSION:")
    print(json.dumps(session_to_dict(session), indent=2))


if __name__ == "__main__":
    main()
