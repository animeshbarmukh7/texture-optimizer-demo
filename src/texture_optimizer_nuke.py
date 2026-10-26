import json
import sys
from pathlib import Path

import nuke


def main() -> int:
    """Execute resize jobs and write structured per-file results."""
    if len(sys.argv) != 4:
        print("Expected: graph_path texture_data_json report_json", file=sys.stderr)
        return 2

    nuke_script_path = sys.argv[1]
    texture_data_json = sys.argv[2]
    report_json = Path(sys.argv[3])

    with open(texture_data_json, "r", encoding="utf-8") as f:
        dct = json.load(f)

    failed_textures = []
    succeeded = []
    errors = {}

    try:
        nuke.scriptOpen(nuke_script_path)

        resize_node = nuke.toNode("TEXTURE_RESIZER")

        if resize_node is None:
            raise ValueError("Nuke graph is missing TEXTURE_RESIZER")

        for name in (
            "input_file",
            "output_file",
            "output_width",
            "output_height",
            "execute_resizing",
        ):
            if resize_node.knob(name) is None:
                raise ValueError(f"TEXTURE_RESIZER is missing knob: {name}")

        for file_path, texture_data in dct.items():
            print(f"Resizing {file_path} with Nuke.", flush=True)

            try:
                width = texture_data["width"]
                height = texture_data["height"]

                if any(
                    type(value) is not int or value <= 0 for value in (width, height)
                ):
                    raise ValueError("Output dimensions must be positive integers")

                resize_node.knob("input_file").setValue(file_path)
                resize_node.knob("output_file").setValue(file_path)
                resize_node.knob("output_width").setValue(width)
                resize_node.knob("output_height").setValue(height)

                resize_node.knob("execute_resizing").execute()

            except Exception as error:
                print(f"Failed to resize {file_path}: {error}", file=sys.stderr)

                failed_textures.append(file_path)
                errors[file_path] = str(error)

            else:
                succeeded.append(file_path)

    except Exception as error:
        print(f"Nuke worker failed: {error}", file=sys.stderr)

        for file_path in dct:
            if file_path not in succeeded and file_path not in failed_textures:
                failed_textures.append(file_path)
                errors[file_path] = str(error)

    with report_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "succeeded": succeeded,
                "failed": failed_textures,
                "errors": errors,
            },
            f,
            indent=2,
        )

    return 1 if failed_textures else 0


if __name__ == "__main__":
    raise SystemExit(main())
