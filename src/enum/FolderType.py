from enum import Enum

class FolderType(Enum):
    METADATA = "m"
    FRAMES = "f"
    GPS = "g"
    BATHY = "b"


def get_foldertype_from_value(char: str) -> FolderType:
    if char == "m": return FolderType.METADATA
    if char == "f": return FolderType.FRAMES
    if char == "g": return FolderType.GPS
    if char == "b": return FolderType.BATHY


def get_full_folder() -> list[FolderType]:
    return [
        FolderType.METADATA,
        FolderType.GPS,
        FolderType.FRAMES,
        FolderType.BATHY
    ]
