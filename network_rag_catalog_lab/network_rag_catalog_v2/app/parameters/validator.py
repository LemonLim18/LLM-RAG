from jsonschema import Draft202012Validator


def validate_parameters(params: dict, schema: dict) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(params), key=lambda e: list(e.path))
    if errors:
        lines = []
        for error in errors:
            path = ".".join(map(str, error.path)) or "<root>"
            lines.append(f"- {path}: {error.message}")
        raise ValueError("Schema validation failed:\n" + "\n".join(lines))
