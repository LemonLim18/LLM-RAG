from jsonschema import Draft202012Validator

def validate_parameters(params,schema):
    # Validate the extracted parameters against the schema.
    # If error happens, raise a ValueError with the error message. Otherwise, return None.
    errors=sorted(Draft202012Validator(schema).iter_errors(params),key=lambda e:list(e.path))
    if errors:
        raise ValueError('Schema validation failed:\n'+'\n'.join(f"- {'.'.join(map(str,e.path)) or '<root>'}: {e.message}" for e in errors))
