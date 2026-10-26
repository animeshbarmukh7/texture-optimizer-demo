import json
from pathlib import Path
from typing import Any

from constants import DEFAULT_JSON_CONFIG_PATH
from logging_setup import logger


class ConfigParser:
    json_config_file: str = DEFAULT_JSON_CONFIG_PATH

    def __init__(self, input_config_path: str | None = None) -> None:
        self.json_config_file = (
            input_config_path
            if input_config_path is not None
            else self.json_config_file
        )
        self.data = self.parse_json_data()

    def parse_json_data(self) -> dict[str, Any]:
        """Read the selected JSON configuration file."""
        logger.debug("Parsing file: %s", self.json_config_file)

        with Path(self.json_config_file).open("r", encoding="utf-8") as f:
            json_data = json.load(f)

        if not isinstance(json_data, dict):
            raise TypeError("Configuration must contain a JSON object.")

        return json_data


class Config:
    PIXEL_MAX_VALUE: float
    NO_OF_PIXEL_RATIO_THRESHOLD_MIN: float
    NO_OF_PIXEL_RATIO_THRESHOLD_MAX: float

    REDUCED_SPECULAR_TEXTURE_SIZE: float
    REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE: float
    REDUCED_HAIR_SPECULAR_TEXTURE_SIZE: float
    REDUCED_MASK_TEXTURE_SIZE: float

    FOREARMS_TEXTURE_SIZE: float
    CALVES_TEXTURE_SIZE: float
    HELMET_TEXTURE_SIZE: float
    THIGHS_TEXTURE_SIZE: float
    CHEST_TEXTURE_SIZE: float

    EXCLUSION_LIST: list[str]
    ALWAYS_IGNORE: list[str]

    __data: dict[str, Any]

    @classmethod
    def load(cls, input_config_path: str | None = None) -> None:
        """Load configuration explicitly during application startup."""
        cls.__data = ConfigParser(input_config_path).data

        cls.PIXEL_MAX_VALUE = float(cls.__data.get("pixel_max_value", 70))

        cls.NO_OF_PIXEL_RATIO_THRESHOLD_MIN = float(
            cls.__data.get(
                "no_of_pixel_ratio_threshold_range", {"min": 5, "max": 8}
            ).get("min")
        )

        cls.NO_OF_PIXEL_RATIO_THRESHOLD_MAX = float(
            cls.__data.get(
                "no_of_pixel_ratio_threshold_range", {"min": 5, "max": 8}
            ).get("max")
        )

        cls.REDUCED_SPECULAR_TEXTURE_SIZE = float(
            cls.__data.get("reduced_specular_texture_size", 64)
        )

        cls.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE = float(
            cls.__data.get("reduced_edge_case_specular_texture_size", 64)
        )

        cls.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE = float(
            cls.__data.get("reduced_hair_specular_texture_size", 1024)
        )

        cls.REDUCED_MASK_TEXTURE_SIZE = float(
            cls.__data.get("reduced_mask_texture_size", 64)
        )

        cls.FOREARMS_TEXTURE_SIZE = float(cls.__data.get("forearms_texture_size", 1024))

        cls.CALVES_TEXTURE_SIZE = float(cls.__data.get("calves_texture_size", 1024))

        cls.HELMET_TEXTURE_SIZE = float(cls.__data.get("helmet_texture_size", 1024))

        cls.THIGHS_TEXTURE_SIZE = float(cls.__data.get("thighs_texture_size", 1024))

        cls.CHEST_TEXTURE_SIZE = float(cls.__data.get("chest_texture_size", 2048))

        cls.EXCLUSION_LIST = cls.__data.get("exclusion_list", [])
        cls.ALWAYS_IGNORE = ["hairstyle_"]
