"""Cached, validated reads of the existing JSON arrays with defensive copies."""

import json
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel, ValidationError

from .models import Category, CategoryParameter, Operation, OperationParameterMapping, OperationSchemaRule, ParameterDefinition


RecordT = TypeVar("RecordT", bound=BaseModel)


class FileKnowledgeRepository:
    def __init__(self, *, categories_file: Path, operations_file: Path, parameters_file: Path,
                 category_parameters_file: Path | None = None,
                 operation_parameters_file: Path | None = None, operation_rules_file: Path | None = None):
        self.categories_file = Path(categories_file)
        self.operations_file = Path(operations_file)
        self.parameters_file = Path(parameters_file)
        self.category_parameters_file = (
            Path(category_parameters_file) if category_parameters_file is not None
            else self.parameters_file.with_name("category_parameters.json")
        )
        self.operation_parameters_file = Path(operation_parameters_file) if operation_parameters_file is not None else self.operations_file.with_name("operation_parameters.json")
        self.operation_rules_file = Path(operation_rules_file) if operation_rules_file is not None else self.operations_file.with_name("operation_rules.json")
        self._cache: dict[tuple[Path, type[BaseModel]], tuple[BaseModel, ...]] = {}

    def _read(self, path: Path, record_type: type[RecordT]) -> list[RecordT]:
        from .authoring_store import ensure_readable
        ensure_readable(path.parent)
        key = (path, record_type)
        if key not in self._cache:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON catalog {path}: {exc}") from exc
            if not isinstance(raw, list):
                raise ValueError(f"Catalog {path} must contain a JSON array.")
            records = []
            for index, item in enumerate(raw):
                try:
                    records.append(record_type.model_validate(item))
                except ValidationError as exc:
                    raise ValueError(f"Invalid catalog record {path}[{index}]: {exc}") from exc
            self._cache[key] = tuple(records)
        return [cast(RecordT, record).model_copy(deep=True) for record in self._cache[key]]

    def list_categories(self) -> list[Category]:
        return self._read(self.categories_file, Category)

    def list_operations(self) -> list[Operation]:
        return self._read(self.operations_file, Operation)

    def list_parameters(self) -> list[ParameterDefinition]:
        return self._read(self.parameters_file, ParameterDefinition)

    def list_category_parameters(self) -> list[CategoryParameter]:
        return self._read(self.category_parameters_file, CategoryParameter)

    def list_operation_parameters(self) -> list[OperationParameterMapping]:
        return self._read(self.operation_parameters_file, OperationParameterMapping)

    def list_operation_rules(self) -> list[OperationSchemaRule]:
        return self._read(self.operation_rules_file, OperationSchemaRule)

    def reload(self) -> None:
        self._cache.clear()
