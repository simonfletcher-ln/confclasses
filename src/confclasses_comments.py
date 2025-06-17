import confclasses
from warnings import deprecated

@deprecated("Use confclasses.save instead")
def save_config(config, stream):
    return confclasses.save(config, stream, comments=True)
