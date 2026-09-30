"""Defensive, typed reads of a candidate JSON document set before committing."""

from copy import deepcopy

from .models import Category, CategoryParameter, Operation, OperationParameterMapping, OperationSchemaRule, ParameterDefinition


class DocumentKnowledgeRepository:
    def __init__(self, documents):
        self._documents = deepcopy(documents)

    def _read(self, name, model):
        records = self._documents[name]
        if not isinstance(records, list):
            raise ValueError(f"{name} must be an array.")
        return [model.model_validate(deepcopy(record)) for record in records]

    def list_categories(self):
        return self._read("categories", Category)

    def list_parameters(self):
        return self._read("parameters", ParameterDefinition)

    def list_operations(self):
        return self._read("operations", Operation)

    def list_category_parameters(self):
        return self._read("category_parameters", CategoryParameter)

    def list_operation_parameters(self):
        return self._read("operation_parameters", OperationParameterMapping)

    def list_operation_rules(self):
        return self._read("operation_rules", OperationSchemaRule)

    def reload(self):
        pass
