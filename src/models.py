from pathlib import Path
from typing import ClassVar

from config import Config


class ImageTuple:
    """Store image dimensions."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height


class TextureStat:
    """Store pixel counts for successfully processed textures."""

    NO_OF_PIXELS_BEFORE: ClassVar[float] = 0
    NO_OF_PIXELS_AFTER: ClassVar[float] = 0


class TextureData:
    """Store target dimensions and associated texture paths."""

    def __init__(self, texture_size: float) -> None:
        self.texture_size: tuple[float, float] = (
            texture_size,
            texture_size,
        )
        self.texture_paths: list[Path] = []


class TextureCollection:
    """Store classifications, planned jobs, and execution outcomes."""

    SPECULAR_TEXTURES: ClassVar[set[Path]] = set()
    MASK_TEXTURES: ClassVar[set[Path]] = set()

    VALID_TEXTURES_SET: ClassVar[set[Path]] = set()

    DOWNSCALE_SPECULAR_TEXTURES: ClassVar[set[Path]] = set()
    DOWNSCALE_EDGE_CASE_SPECULAR_TEXTURES: ClassVar[set[Path]] = set()
    DOWNSCALE_HAIR_SPECULAR_TEXTURES: ClassVar[set[Path]] = set()
    DOWNSCALE_MASK_TEXTURES: ClassVar[set[Path]] = set()

    TEXTURE_MAPPING_DICT: ClassVar[dict[str, TextureData]] = {}

    TEXTURES_TO_BE_PROCESSED: ClassVar[dict[str, dict[str, float]]] = {}

    PROCESSED_TEXTURES: ClassVar[list[str]] = []

    CHECKOUT_FAILED: ClassVar[list[str]] = []
    PREPROCESSING_FAILED: ClassVar[list[str]] = []
    DELETION_FAILED: ClassVar[list[str]] = []
    NUKE_RESIZE_FAILED: ClassVar[list[str]] = []

    @classmethod
    def initialize_texture_mapping(cls) -> None:
        """Build the texture mapping after Config.load() completes."""
        cls.TEXTURE_MAPPING_DICT = {
            "_calves": TextureData(Config.CALVES_TEXTURE_SIZE),
            "_chest": TextureData(Config.CHEST_TEXTURE_SIZE),
            "_forearms": TextureData(Config.FOREARMS_TEXTURE_SIZE),
            "_helmet": TextureData(Config.HELMET_TEXTURE_SIZE),
            "_thighs": TextureData(Config.THIGHS_TEXTURE_SIZE),
        }
