from enum import Enum


class StatusChoices(str, Enum):
    planned = "planned"
    in_progress = "in_progress"
    on_hold = "on_hold"
    discharged = "discharged"
    completed = "completed"
    cancelled = "cancelled"
    discontinued = "discontinued"
    entered_in_error = "entered_in_error"
    unknown = "unknown"


COMPLETED_CHOICES = [
    StatusChoices.completed.value,
    StatusChoices.cancelled.value,
    StatusChoices.entered_in_error.value,
    StatusChoices.discontinued.value,
]


class ClassChoices(str, Enum):
    imp = "imp"
    amb = "amb"
    obsenc = "obsenc"
    emer = "emer"
    vr = "vr"
    hh = "hh"


class AdmitSourcesChoices(str, Enum):
    hosp_trans = "hosp_trans"
    emd = "emd"
    outp = "outp"
    born = "born"
    gp = "gp"
    mp = "mp"
    nursing = "nursing"
    psych = "psych"
    rehab = "rehab"
    other = "other"


class DischargeDispositionChoices(str, Enum):
    home = "home"
    alt_home = "alt_home"
    other_hcf = "other_hcf"
    hosp = "hosp"
    long = "long"
    aadvice = "aadvice"
    exp = "exp"
    psy = "psy"
    rehab = "rehab"
    snf = "snf"
    oth = "oth"


class DietPreferenceChoices(str, Enum):
    vegetarian = "vegetarian"
    dairy_free = "dairy_free"
    nut_free = "nut_free"
    gluten_free = "gluten_free"
    vegan = "vegan"
    halal = "halal"
    kosher = "kosher"
    none = "none"


class EncounterPriorityChoices(str, Enum):
    ASAP = "ASAP"
    callback_results = "callback_results"
    callback_for_scheduling = "callback_for_scheduling"
    elective = "elective"
    emergency = "emergency"
    preop = "preop"
    as_needed = "as_needed"
    routine = "routine"
    rush_reporting = "rush_reporting"
    stat = "stat"
    timing_critical = "timing_critical"
    use_as_directed = "use_as_directed"
    urgent = "urgent"
