import os
from pathlib import Path

VERSION: str = "0.1.0"

PACKAGE_ROOT: Path = Path(__file__).parent

LOG_DIRECTORY: str = os.path.expandvars(r"%APPDATA%\AGS_LOG\Texture_optimizer")

DEFAULT_JSON_CONFIG_PATH: str = (
    PACKAGE_ROOT / "config" / "texture_optimizer_config.json"
).as_posix()

ERROR_REPORT: Path = Path(LOG_DIRECTORY) / "error_report.txt"

# Maximum wall-clock time for one Nuke batch, in seconds.
NUKE_TIMEOUT_SECONDS: int = 3600
