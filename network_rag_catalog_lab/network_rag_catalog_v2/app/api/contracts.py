""""
contracts.py is building a higher-level request objects using lower-level knowledge models.
These higher-level requests allows the management layer to be more expressive and easier to use.
"""

"""Strict envelopes for a local CLI and a future authenticated API."""

# Literal type only allows for string values that are explicitly defined, and not other than that, providing like a list of strring options to be chosen.
from typing import Literal
# BaseModal makes this class a Pydantic model, which provides data validation and serialization capabilities
# The BaseModel model can be added into a self-defined class, making it a Pydantic model, which will provide the capabilities of data validation and serialization. 
# ConfigDict configures how that model behaves, such as whether to allow extra fields or not
# Field add rules/defaults/constraints to the fields of the model, such as minimum length or default values.
from pydantic import BaseModel, ConfigDict, Field

from ..knowledge.models import NonBlankText, StableId, OperationParameterMapping, OperationSchemaRule, TemplateBinding

# Now, we define a base class called Contract that inherits from BaseModel, which has the capabilities of data validation and construction for an object. This class is used as a general common class for all the data structures that will be used in the management layer. 
# It has a model_config attribute that specifies that the model should not allow any extra fields beyond those defined in the class.
# ConfigDict is used to define the rules & configure the behavior of the Pydantic model. 
# strict=True makes the Pydantic model be strict about the types instead of helpfully converting the things.
# extra="forbid" rejects fields that are not defined in the model.
# This base class can be used as a parent class for other data structures that will be defined in the management layer.
class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

# This class represents one thing the engineer wants to change in the catalog.
# For example, if the engineer wants to create a new category, they would create an EntityChange object with entity="category", action="create", and values containing the details of the new category.
class EntityChange(Contract):
    # Here, we define that the entity should be of string type, and only be one of the following literal values.
    # entity represents the type of entity that is being changed.
    entity: Literal["category", "parameter", "operation", "membership", "contract", "context_rules"]
    action: Literal["create", "update", "delete", "retire", "assign", "unassign", "replace"]
    # entity_id represents the unique identifier of the entity
    entity_id: StableId | None = None
    # {
    #     "display_name": "Create VLAN",
    #     "category_id": "switching"
    # }
    values: dict = Field(default_factory=dict)  # If the caller doesnt provide values, create an empty dict by default.


# OperationContractInput describes for this version of an operation, what parameters exist, what rules apply to them, and what templates can consume them.
class OperationContractInput(Contract):
    version: int = Field(ge=1) # the version should be greater than or equal to 1

    # A list of parameter mappings for this operation
    mappings: list[OperationParameterMapping] # which parameters are used.
    rules: list[OperationSchemaRule] # what constraints apply to those parameters. E.g. "this field is required if that field is set to this value" and "this field must be minimum 1 character long"
    templates: list[TemplateBinding] # what templates is bound to this operation, helps rendering these parameters for Cisco/Huawei/Juniper and what versions of those templates are compatible with this operation version.

"""
Operation: create_vlan
Version: 1

    mappings
    ────────
    vlan_id (GLOBAL) -> vlan_id
    name    (GLOBAL) -> name


    rules
    ─────
    vlan_id:
        minimum = 1
        maximum = 4094


    templates
    ─────────
    Cisco IOS-XE -> cisco/.../template.j2
    Huawei VRP   -> huawei/.../template.j2
    Junos        -> junos/.../template.j2

# Note: Template written againt Version 1 isn't automatically assumed compatible with Version 2. The template must be explicitly bound to Version 2 as well.
"""

# This class represents "I want to modify the knowledge store/catalog" in one edit.
# One edit request can contain multiple changes. That matters as the managed system supports transactions, so either all changes succeed or none of them do.
class EditRequest(Contract):
    expected_revision: NonBlankText   # This protects against editing stale data. E.g. both editor see database of revision 20, mark it as expected revision, another editor makes it to 21, then first editor sends revision 20, which service will reject as stale.
    actor: NonBlankText    
    reason: NonBlankText        # But the reason written by who?
    changes: list[EntityChange] = Field(min_length=1)       # This allows multiple EntityChange within one EditRequest, which is useful for atomicity. E.g. if you want to create a new category and then create a new operation within that category, you can do it in one EditRequest, so either both succeed or both fail.

"""
Architecture Note:
Engineer edits

    └─> EditRequest
        ├─> EntityChange
        │   ├─> entity: "category"
        │   ├─> action: "create"
        │   └─> values: { "display_name": "Create VLAN", "category_id": "switching" }
        └─> EntityChange
            ├─> entity: "operation"
            ├─> action: "create"
            └─> values: { "operation_id": "create_vlan", "category_id": "switching", ... }
      ↓
 SQLite draft (The SQLite draft is a temporary storage of the changes made in the EditRequest. It allows the engineer to make changes to the catalog without affecting the live system. The draft can be validated and tested before being published to the live system.)
      ↓
  validation (The validation step checks the changes made in the EditRequest against the current state of the catalog. It ensures that the changes are valid and consistent with the existing data. If any issues are found, they are reported back to the engineer for correction before proceeding to the next step.)
      ↓
 PublishRequest (PublishRequest is a request to publish the changes made in the EditRequest to the catalog. It contains information about the expected revision, actor, reason, and mode of publishing.)
      ↓
   compiler (The compiler takes the validated changes and generates the necessary artifacts, such as templates, schemas, and other resources required for the operation to function correctly. It ensures that all dependencies are resolved and that the generated artifacts are consistent with the catalog's current state.)
      ↓
 immutable release (The immutable release is a versioned snapshot of the catalog that is created after the changes have been published. It ensures that the catalog remains consistent and can be rolled back to a previous state if needed. Each release is uniquely identified and cannot be modified, providing a reliable reference for future operations.)
      ↓
   runtime (The runtime is the environment where the catalog is executed and used by the system. It includes the necessary components, such as the database, application logic, and user interfaces, to interact with the catalog. The runtime ensures that the catalog operates correctly and efficiently, providing the expected functionality to users and other systems.)
"""

class PublishRequest(Contract):
    # expected_revision is used to ensure that the changes being published are based on the latest version of the catalog. If the expected_revision does not match the current revision in the catalog, the publish request will be rejected to prevent overwriting changes made by other users.
    expected_revision: NonBlankText     # This protects against publishing stale data. E.g. both editor see database of revision 20, mark it as expected revision, another editor makes it to 21, then first editor publishes revision 21, which service will reject as stale.
    expected_release: str | None        # This is the currently expected published release, if your current active release is 10, but someone has meanwhile published release 11, the system detect your assumption is stale
    actor: NonBlankText
    reason: NonBlankText
    # mode: offline -> publication without the normal Chroma indexing path; chroma -> publication with the normal Chroma indexing path. The offline mode is useful for testing and debugging, as it allows the engineer to publish changes without affecting the live system. The chroma mode is the default mode for publishing changes to the live system, ensuring that the changes are indexed and available for use by other components of the system.
    mode: Literal["offline", "chroma"] = "chroma"

# Perform a knowledge migration, which is a change to the underlying data model or schema of the catalog. This may be necessary when new features are added, or when existing features are modified or deprecated. The migration request includes the expected revision, actor, and reason for the migration, ensuring that the changes are applied in a controlled and auditable manner.
class MigrationRequest(Contract):
    expected_revision: NonBlankText     # This protects against applying stale migrations. E.g. both editor see database of revision 20, mark it as expected revision, another editor makes it to 21, then first editor sends revision 20, which service will reject as stale.
    actor: NonBlankText
    reason: NonBlankText

# CatalogExport helps generate the portable bundle of knowledge
class CatalogExport(Contract):
    format_version: Literal[1] = 1
    revision: str       # which knowledge version produced this export, e.g. "2023-08-01T12:34:56Z"
    catalogs: dict[str, list | dict]    # contains the actual knowledge records
    asset_hashes: dict[str, str]    # contains the hashes of the assets, like templates to let the system identify whether associated assets have changed or match the expected export.

# Opposite side of CatalogExport, which imports the portable bundle of knowledge into the system.
"""
    CatalogExport
          ↓
    portable bundle
          ↓
    ImportRequest
          ↓
    management layer
          ↓
    authoring store
"""
class ImportRequest(Contract):
    expected_revision: NonBlankText
    actor: NonBlankText
    reason: NonBlankText
    bundle: CatalogExport

# This represents one structured problem.
class ManagementIssue(Contract):
    code: str   # what kind of error?
    path: str = ""  # where
    message: str    # what should human read?

# standard answer returned by the management layer
class ManagementResult(Contract):
    ok: bool
    revision: str | None = None
    data: dict = Field(default_factory=dict)
    issues: list[ManagementIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
