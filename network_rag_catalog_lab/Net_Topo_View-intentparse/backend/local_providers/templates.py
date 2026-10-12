"""Existing renderer/validators with local SQLite source revisions."""
from jinja2 import FunctionLoader
from jinja2.sandbox import SandboxedEnvironment
from config_engine.renderer import TemplateRenderer, SUPPORTED_VENDORS
from .authoring import AuthoringStore
import json

class LocalTemplateRenderer(TemplateRenderer):
    def __init__(self, store=None):
        self._store=store
        super().__init__()
        self.env=SandboxedEnvironment(loader=FunctionLoader(self.load),trim_blocks=True,lstrip_blocks=True,keep_trailing_newline=True,cache_size=0)

    @property
    def store(self):
        return self._store or AuthoringStore()

    def load(self,path):
        try: return self.store.read('templates',path)
        except FileNotFoundError: return None

    def get_template_content(self,vendor,feature):
        return self.store.read('templates',f'{vendor}/{feature}.j2')

    def get_schema(self,feature):
        try: return json.loads(self.store.read('schemas',f'{feature}.json'))
        except FileNotFoundError: return None

    def list_templates(self,vendor=None):
        if vendor: self._validate_vendor(vendor)
        items=self.store.entries('templates')
        schemas=self.store.entries('schemas')
        return [{'vendor':p.split('/')[0],'feature':p.split('/')[1][:-3],
                 'has_undo':p.split('/')[0]+'/undo_'+p.split('/')[1] in items,
                 'schema_exists':p.split('/')[1][:-3]+'.json' in schemas,
                 'source':'stored','revision':m['revision']}
                for p,m in sorted(items.items()) if not p.split('/')[1].startswith('undo_') and (not vendor or p.startswith(vendor+'/'))]

    def _validate_params(self,feature,params):
        errors=super()._validate_params(feature,params)
        schema=self.get_schema(feature)
        if schema:
            from jsonschema import Draft202012Validator
            errors.extend(e.message for e in Draft202012Validator(schema).iter_errors(params))
        return errors
