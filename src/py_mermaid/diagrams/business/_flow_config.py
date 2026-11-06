"""Project shared flowchart-rendering settings without family configuration loss."""
from ...config.flowchart import _ROOT_KEYS,resolve_config

def flow_config(config,*,measurement_only=False):
    # Generic registry configuration contains all diagram sections. The F014
    # resolver deliberately rejects unknown sections; select its declared
    # input surface while the family keeps the original full configuration.
    values={key:value for key,value in config.items() if key in _ROOT_KEYS}
    if measurement_only:values['layout']='elk'
    return resolve_config(values)
