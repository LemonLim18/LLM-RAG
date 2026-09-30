"""Local knowledge management CLI. Request files are JSON; there is no network API."""

import argparse
import json
from pathlib import Path

from ..api.contracts import ManagementIssue, ManagementResult
from ..config import BASE_DIR
from .management import KnowledgeManagementService


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=BASE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "validate", "export", "recover"):
        commands.add_parser(name)
    preview = commands.add_parser("preview-schema")
    preview.add_argument("operation_id")
    preview.add_argument("--vendor")
    for name in ("apply", "import", "publish", "migrate-sqlite"):
        command = commands.add_parser(name)
        command.add_argument("request", type=Path)
        if name == "apply":
            command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    manager = KnowledgeManagementService(args.project)
    try:
        if args.command == "preview-schema":
            result = manager.preview_schema(args.operation_id, args.vendor)
        elif args.command in {"apply", "import", "publish", "migrate-sqlite"}:
            request = json.loads(args.request.read_text(encoding="utf-8"))
            if args.command == "apply":
                result = manager.apply(request, dry_run=args.dry_run)
            elif args.command == "import":
                result = manager.import_catalog(request)
            elif args.command == "migrate-sqlite":
                result = manager.migrate_sqlite(request)
            else:
                result = manager.publish(request)
        else:
            result = getattr(manager, args.command)()
    except (OSError, ValueError) as exc:
        result = ManagementResult(ok=False, issues=[ManagementIssue(code="INVALID_REQUEST", message=str(exc))])
    print(result.model_dump_json(indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
