from enum import Enum

class StandardDeviationType(Enum):
    NORTH = "sdn"
    EAST = "sde"


def get_title_based_on_sd_type(sd_type: StandardDeviationType) -> str:
    if sd_type == StandardDeviationType.NORTH:
        return "Sdn"
    return "Sde"