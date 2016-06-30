from jinja2 import Markup
from dxr.filters import QualifiedNameFilterBase
from dxr.plugins.js.refs import PLUGIN_NAME


class _QualifiedNameFilter(QualifiedNameFilterBase):
    lang = PLUGIN_NAME


class PropFilter(_QualifiedNameFilter):
    name = 'prop'
    suggest_prop = 'js_prop_suggest'
    is_identifier = True
    description = Markup('JavaScript property definition filter: <code>prop:foo</code>')


class PropRefFilter(_QualifiedNameFilter):
    name = 'prop-ref'
    suggest_prop = 'js_prop_ref_suggest'
    is_reference = True
    description = 'References to JavaScript object properties'


class VarFilter(_QualifiedNameFilter):
    name = 'var'
    suggest_prop = 'js_var_suggest'
    is_identifier = True
    description = Markup('Variable definition: <code>var:foo</code>')


class VarRefFilter(_QualifiedNameFilter):
    name = 'var-ref'
    suggest_prop = 'js_var_ref_suggest'
    is_reference = True
    description = 'Function or method references'
