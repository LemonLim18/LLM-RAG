"""Typed shared definitions, operation contracts and template bindings."""

from typing import Annotated, Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator


StableId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
NonBlankText = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
FieldPath = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\]|\.[A-Za-z_][A-Za-z0-9_]*)*$")]
NodePath = Annotated[str, StringConstraints(pattern=r"^(?:[A-Za-z_][A-Za-z0-9_]*(?:\[\]|\.[A-Za-z_][A-Za-z0-9_]*)*)?$")]


class CatalogRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="allow")

    display_name: NonBlankText
    aliases: list[NonBlankText] = Field(default_factory=list)
    description: str = ""

    def to_legacy_dict(self) -> dict:
        # Do not inject model defaults into existing callers' dictionary payloads.
        return self.model_dump(exclude_unset=True)


class Category(CatalogRecord):
    category_id: StableId
    status: Literal["active", "inactive"] = "active"


class ParameterDefinition(CatalogRecord):
    parameter_id: StableId
    value_type: Literal["string", "integer", "number", "boolean", "array", "object", "null"]
    clarification: str = ""
    normalizer: NonBlankText | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_operation_policies(cls, value):
        policy_keys = set(Draft202012Validator.VALIDATORS) | {
            "optional", "validation", "validation_rules", "rules", "schema", "default", "x-required-by-vendor",
        }
        if isinstance(value, dict) and (found := policy_keys.intersection(value)):
            raise ValueError(f"Operation rules belong in operation schemas, not shared parameters: {sorted(found)}")
        return value


class CategoryParameter(BaseModel):
    """Membership only; labels/types remain on the referenced definition."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    category_id: StableId
    parameter_id: StableId


class VendorIntentKnowledge(BaseModel):
    """Intent recognition is independent of reviewed configuration support."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    status: Literal["generation_supported", "blocked_unverified"]
    reason: NonBlankText
    requirements: list[NonBlankText] = Field(default_factory=list)


class Operation(CatalogRecord):
    operation_id: StableId
    category_id: StableId
    schema_path: str = ""
    status: Literal["active", "inactive"] = "active"
    version: Annotated[int, Field(ge=1)] = 1
    use_cases: list[NonBlankText] = Field(default_factory=list)
    schema_source: Literal["legacy", "registry"] = "legacy"
    mapping_mode: Literal["none", "compare"] = "none"
    vendor_knowledge: dict[StableId, VendorIntentKnowledge] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_authority(self):
        if self.schema_source == "legacy" and not self.schema_path.strip():
            raise ValueError("Legacy operations require a schema_path.")
        if self.schema_source == "registry" and self.mapping_mode != "none":
            raise ValueError("Registry authority cannot also be comparison-only.")
        return self


class TemplateInputContract(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    fields: list[NonBlankText]
    optional_defaults: dict[str, None] = Field(default_factory=dict)
    derived: dict[str, str] = Field(default_factory=dict)


class ConditionalRequirement(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    field: NonBlankText
    equals: JsonValue
    required: Annotated[list[NonBlankText], Field(min_length=1)]


class TemplateBinding(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    operation_id: StableId
    operation_version: Annotated[int, Field(ge=1)]
    vendor: StableId
    platform: StableId
    versions: Annotated[list[NonBlankText], Field(min_length=1)]
    template_path: NonBlankText
    input_contract: TemplateInputContract


class OperationParameterMapping(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    operation_id: StableId
    operation_version: Annotated[int, Field(ge=1)]
    category_id: StableId
    parameter_id: StableId
    field_path: FieldPath
    position: Annotated[int, Field(ge=0)]
    required: bool
    required_order: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def check_required_order(self):
        if self.required != (self.required_order is not None):
            raise ValueError("Required fields need a required_order; optional fields must use null.")
        if self.field_path.endswith("[]"):
            raise ValueError("Mappings identify named properties, not anonymous array items.")
        return self


class OperationSchemaRule(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    operation_id: StableId
    operation_version: Annotated[int, Field(ge=1)]
    field_path: NodePath
    keywords: dict[str, JsonValue]

    @model_validator(mode="after")
    def check_structural_keywords(self):
        if set(self.keywords) & {"properties", "items", "required"}:
            raise ValueError("Property structure and required flags belong to mappings, not rule keywords.")
        return self
