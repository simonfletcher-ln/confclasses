# Confclasses

The idea is to handle loading/saving the config from files while allowing simpler IDE usage with the config. We dont 
need 90% of the features in dataclasses, so we make the api easier.


The module is designed to have a global config object that is instantiated at the start and then loaded dynamically
later. This is why the dataclass __init__ is pushed aside and we run it manually later.

