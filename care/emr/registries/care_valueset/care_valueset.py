from care.emr.fhir.resources.valueset import ValueSetResource
from care.emr.models.valueset import ValueSet as ValuesetDatabaseModel
from care.emr.resources.common.valueset import ValueSet, ValueSetCompose


class CareValueset:
    """
    Care Valueset is a pre-system defined valueset which can be enhanced by plugs
    Eg, A Disease valueset can be system created and used for all system related API's
    This valueset will be initially empty, but plugs can register their values into this valueset
    as they are added. This allows for a pluggable valueset concept

    Valuesets are written to the database using a management command, they can be reset based on this as well.
    These valuesets can then be edited to the admins requirements
    """

    slug = None
    name = None
    status = None

    def __init__(self, name, slug, status, compose=None):
        self.name = name
        self.slug = slug
        self.status = status
        if compose:
            self.composition = compose
        else:
            self.composition = ValueSetCompose(include=[], exclude=[])

    def register_as_system(self):
        SystemValueSet.add_system_valueset(self)

    def register_valueset(self, composition: ValueSetCompose):
        """
        Register a valueset to the system
        """
        if composition.include:
            for include in composition.include:
                self.composition.include.append(include)
        if composition.exclude:
            for exclude in composition.exclude:
                self.composition.exclude.append(exclude)

    @property
    def valueset(self):
        return ValueSet(name=self.name, status=self.status, compose=self.composition)

    def create_composition(self):
        systems = {}
        for include in self.composition.include:
            system = include.system
            if system not in systems:
                systems[system] = {"include": []}
            systems[system]["include"].append(include.model_dump(exclude_defaults=True))
        for exclude in self.composition.exclude:
            system = exclude.system
            if system not in systems:
                systems[system] = {"exclude": []}
            systems[system]["exclude"].append(exclude.model_dump(exclude_defaults=True))
        return systems

    def search(self, filter=""):
        # Create a composition with the same system
        # Query each system
        # Combine and return
        systems = self.create_composition()

        results = []

        for system in systems:
            results.extend(
                ValueSetResource()
                .filter(search=filter, count=10, **systems[system])
                .search()
            )
        return results


class SystemValueSet:
    _valuesets = []

    @classmethod
    def add_system_valueset(cls, valueset: CareValueset):
        cls._valuesets.append(valueset)

    @classmethod
    def get_all_valuesets(cls):
        return cls._valuesets


def validate_valueset(field, slug, code):
    valueset_obj = ValuesetDatabaseModel.objects.filter(slug=slug).first()
    if not valueset_obj:
        err = "Valueset does not exist in care, Resync valuesets"
        raise ValueError(err)
    exists = valueset_obj.lookup(code)
    if not exists:
        err = "Code does not exist in the valueset"
        raise ValueError(err)
    return code
