import json
import os
import subprocess
from pathlib import Path

import file_helper
import numpy as np
from perforce import client
from PIL import Image, ImageStat

from cli import main as cli_main
from config import Config
from constants import ERROR_REPORT, LOG_DIRECTORY, NUKE_TIMEOUT_SECONDS, PACKAGE_ROOT
from logging_setup import logger
from models import ImageTuple, TextureCollection, TextureStat


def get_image_resolution(image_path: Path) -> ImageTuple:
    with Image.open(image_path) as image:
        image.load()
        width, height = image.size

    return ImageTuple(width, height)


def filter_textures() -> None:
    """Find out Mask and Specular textures."""

    for texture_path in TextureCollection.VALID_TEXTURES_SET:
        if file_helper.is_read_only(texture_path.as_posix()):
            logger.debug(
                f"The file {texture_path.as_posix()} was read only making it writable."
            )

            file_helper.make_writeable(texture_path.as_posix())

        texture_name = texture_path.name.lower()

        if "_spec" in texture_name:
            TextureCollection.SPECULAR_TEXTURES.add(texture_path)

        if "_mask" in texture_name:
            TextureCollection.MASK_TEXTURES.add(texture_path)


def process_textures() -> None:
    filter_out_specular_textures()
    filter_out_mask_textures()
    filter_out_textures_by_parts()


def filter_out_specular_textures() -> None:
    """This method process all specular textures found, and categorizes those into following two types:
    1. Textures those need to be downscaled in default way.
    2. Edge case textures those need to be downscaled in special way.
    """

    for specular_image_path in TextureCollection.SPECULAR_TEXTURES:
        logger.info(f"Processing {specular_image_path.as_posix()}")

        try:
            specular_image = Image.open(specular_image_path.as_posix())
            specular_image = specular_image.convert("L")

            image_mtx = np.array(specular_image)
            count = np.count_nonzero(image_mtx >= Config.PIXEL_MAX_VALUE)
            total_pixel_count = float(image_mtx.size)

            # find ratio
            pixel_ratio = (count / total_pixel_count) * 100

            logger.debug(
                f"No of pixels found which were brighter than {Config.PIXEL_MAX_VALUE} are {count}."
            )
            logger.debug(f"Total pixels found are {total_pixel_count}.")
            logger.debug(f"Pixel ratio is {pixel_ratio}.")

        except Exception as error:
            logger.exception(error)
            TextureCollection.PREPROCESSING_FAILED.append(
                specular_image_path.as_posix()
            )
        else:
            if "hairstyle_" in specular_image_path.as_posix().lower():
                TextureCollection.DOWNSCALE_HAIR_SPECULAR_TEXTURES.add(
                    specular_image_path
                )
                logger.debug(
                    f"Classifying {specular_image_path.as_posix()} for hair downscaling."
                )

            elif pixel_ratio < Config.NO_OF_PIXEL_RATIO_THRESHOLD_MIN:
                TextureCollection.DOWNSCALE_SPECULAR_TEXTURES.add(specular_image_path)
                logger.debug(
                    f"Classifying {specular_image_path.as_posix()} for normal downscaling."
                )

            elif (
                Config.NO_OF_PIXEL_RATIO_THRESHOLD_MIN
                <= pixel_ratio
                <= Config.NO_OF_PIXEL_RATIO_THRESHOLD_MAX
            ):
                TextureCollection.DOWNSCALE_EDGE_CASE_SPECULAR_TEXTURES.add(
                    specular_image_path
                )
                logger.debug(
                    f"Classifying {specular_image_path.as_posix()} for edge case downscaling."
                )


def filter_out_mask_textures() -> None:
    """This method process all mask textures found, and filters textures which can be downscaled."""

    for mask_image_path in TextureCollection.MASK_TEXTURES:
        logger.info(f"Processing {mask_image_path.as_posix()}")

        try:
            mask_image = Image.open(mask_image_path.as_posix())
            mask_image_stats = ImageStat.Stat(mask_image)

            for mean_val in mask_image_stats.mean:
                if mean_val == 255:
                    TextureCollection.DOWNSCALE_MASK_TEXTURES.add(mask_image_path)
                    break
        except Exception as error:
            logger.exception(error)
            TextureCollection.PREPROCESSING_FAILED.append(mask_image_path.as_posix())


def filter_out_textures_by_parts() -> None:
    """

    Returns:

    """

    mesh_parts_keys = list(TextureCollection.TEXTURE_MAPPING_DICT.keys())

    ignore_list = [
        TextureCollection.DOWNSCALE_SPECULAR_TEXTURES,
        TextureCollection.DOWNSCALE_MASK_TEXTURES,
        TextureCollection.DOWNSCALE_EDGE_CASE_SPECULAR_TEXTURES,
    ]

    # Do not include exempt down scalable specular and mask textures. These textures will be reduced to 64x64 differently.

    new_texture_set = TextureCollection.VALID_TEXTURES_SET
    for ignore_set in ignore_list:
        new_texture_set.difference_update(ignore_set)

    logger.debug(f"Texture set which will be used for processing is {new_texture_set}")

    for texture_path in new_texture_set:
        for part in mesh_parts_keys:
            if part in texture_path.name.lower():
                logger.info(f"Processing {texture_path.as_posix()}")

                TextureCollection.TEXTURE_MAPPING_DICT[part].texture_paths.append(
                    texture_path
                )


def collect_textures_for_downscaling() -> None:
    TextureStat.NO_OF_PIXELS_BEFORE = 0
    for texture_obj in TextureCollection.TEXTURE_MAPPING_DICT.values():
        for texture in texture_obj.texture_paths:
            image = get_image_resolution(texture)
            image_size = (image.width, image.height)
            texture_w, texture_h = texture_obj.texture_size

            if image_size > texture_obj.texture_size:
                logger.info(f"Updating texture -> {texture.as_posix()}")

                width, height = image_size
                TextureStat.NO_OF_PIXELS_BEFORE += width * height
                TextureStat.NO_OF_PIXELS_AFTER += texture_w * texture_h

                TextureCollection.TEXTURES_TO_BE_PROCESSED[texture.as_posix()] = {
                    "width": texture_w,
                    "height": texture_h,
                }

                TextureCollection.PROCESSED_TEXTURES.append(texture.as_posix())

    for texture in TextureCollection.DOWNSCALE_SPECULAR_TEXTURES:
        image = get_image_resolution(texture)
        image_size = (float(image.width), float(image.height))

        if image_size > (
            Config.REDUCED_SPECULAR_TEXTURE_SIZE,
            Config.REDUCED_SPECULAR_TEXTURE_SIZE,
        ):
            logger.info(f"Updating texture -> {texture.as_posix()}.")

            width, height = image_size
            TextureStat.NO_OF_PIXELS_BEFORE += width * height
            TextureStat.NO_OF_PIXELS_AFTER += (
                Config.REDUCED_SPECULAR_TEXTURE_SIZE
                * Config.REDUCED_SPECULAR_TEXTURE_SIZE
            )

            TextureCollection.TEXTURES_TO_BE_PROCESSED[texture.as_posix()] = {
                "width": Config.REDUCED_SPECULAR_TEXTURE_SIZE,
                "height": Config.REDUCED_SPECULAR_TEXTURE_SIZE,
            }

            TextureCollection.PROCESSED_TEXTURES.append(texture.as_posix())

    for texture in TextureCollection.DOWNSCALE_EDGE_CASE_SPECULAR_TEXTURES:
        image = get_image_resolution(texture)
        image_size = (float(image.width), float(image.height))

        if image_size > (
            Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE,
            Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE,
        ):
            logger.info(f"Updating texture -> {texture.as_posix()}.")

            width, height = image_size
            TextureStat.NO_OF_PIXELS_BEFORE += width * height
            TextureStat.NO_OF_PIXELS_AFTER += (
                Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE
                * Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE
            )

            TextureCollection.TEXTURES_TO_BE_PROCESSED[texture.as_posix()] = {
                "width": Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE,
                "height": Config.REDUCED_EDGE_CASE_SPECULAR_TEXTURE_SIZE,
            }

            TextureCollection.PROCESSED_TEXTURES.append(texture.as_posix())

    for texture in TextureCollection.DOWNSCALE_HAIR_SPECULAR_TEXTURES:
        image = get_image_resolution(texture)
        image_size = (float(image.width), float(image.height))

        if image_size > (
            Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE,
            Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE,
        ):
            logger.info(f"Updating texture -> {texture.as_posix()}.")

            width, height = image_size
            TextureStat.NO_OF_PIXELS_BEFORE += width * height
            TextureStat.NO_OF_PIXELS_AFTER += (
                Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE
                * Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE
            )

            TextureCollection.TEXTURES_TO_BE_PROCESSED[texture.as_posix()] = {
                "width": Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE,
                "height": Config.REDUCED_HAIR_SPECULAR_TEXTURE_SIZE,
            }

            TextureCollection.PROCESSED_TEXTURES.append(texture.as_posix())

    for texture in TextureCollection.DOWNSCALE_MASK_TEXTURES:
        image = get_image_resolution(texture)  # type: ImageTuple
        image_size = (float(image.width), float(image.height))

        if image_size > (
            Config.REDUCED_MASK_TEXTURE_SIZE,
            Config.REDUCED_MASK_TEXTURE_SIZE,
        ):
            logger.info(f"Updating texture -> {texture.as_posix()}.")

            width, height = image_size
            TextureStat.NO_OF_PIXELS_BEFORE += width * height
            TextureStat.NO_OF_PIXELS_AFTER += (
                Config.REDUCED_MASK_TEXTURE_SIZE * Config.REDUCED_MASK_TEXTURE_SIZE
            )

            TextureCollection.TEXTURES_TO_BE_PROCESSED[texture.as_posix()] = {
                "width": Config.REDUCED_MASK_TEXTURE_SIZE,
                "height": Config.REDUCED_MASK_TEXTURE_SIZE,
            }

            TextureCollection.PROCESSED_TEXTURES.append(texture.as_posix())


def downscale_textures() -> bool:
    """
    This method uses nuke to reduce texture size.
    """

    nuke_dir = os.getenv("REZ_NUKE_ROOT")
    nuke_version = os.getenv("REZ_NUKE_VERSION")

    if nuke_dir is None or nuke_version is None:
        logger.error("Nuke not found")
        return False

    nuke_major_version = os.getenv("REZ_NUKE_MAJOR_VERSION")
    nuke_minor_version = os.getenv("REZ_NUKE_MINOR_VERSION")

    nuke_path = Path(nuke_dir, f"Nuke{nuke_major_version}.{nuke_minor_version}.exe")
    nuke_script = Path(PACKAGE_ROOT, "nuke", "Texture_Resizing.nk")
    python_script = Path(PACKAGE_ROOT, "texture_optimizer_nuke.py")

    texture_processing_json = Path(LOG_DIRECTORY, "texture_data.json")
    if texture_processing_json.exists():
        os.remove(texture_processing_json.as_posix())

    if ERROR_REPORT.exists():
        os.remove(ERROR_REPORT.as_posix())

    if TextureCollection.PREPROCESSING_FAILED:
        with open(ERROR_REPORT.as_posix(), "w") as f:
            f.write("\nFollowing textures were failed in pre-processing.\n")
            f.writelines(TextureCollection.PREPROCESSING_FAILED)
            f.write("\n")

    with open(texture_processing_json, "w") as f:
        json.dump(TextureCollection.TEXTURES_TO_BE_PROCESSED, f)

    argument_list = [
        nuke_script.as_posix(),
        texture_processing_json.as_posix(),
        ERROR_REPORT.as_posix(),
    ]

    command = [str(nuke_path), "-i", "-t", str(python_script), *argument_list]

    logger.info("Starting Nuke.")

    proc = subprocess.run(
        command,
        stdout=f,
        stderr=subprocess.STDOUT,
        shell=False,
        timeout=NUKE_TIMEOUT_SECONDS,
        check=False,
    )
    stdout = proc.stdout
    stderr = proc.stderr

    logger.debug(stdout.decode())

    if proc.returncode:
        if stderr:
            logger.error(stderr.decode())
        return False

    return True


def print_report() -> None:
    report_json = ERROR_REPORT.parent / "report.json"

    if report_json.exists():
        with open(report_json, "r") as f:
            TextureCollection.NUKE_RESIZE_FAILED = json.load(f)

    total_texture_modified = len(
        TextureCollection.TEXTURES_TO_BE_PROCESSED.keys()
    ) - len(TextureCollection.NUKE_RESIZE_FAILED)

    TextureStat.NO_OF_PIXELS_AFTER = 0
    for texture in TextureCollection.TEXTURES_TO_BE_PROCESSED:
        if texture in TextureCollection.NUKE_RESIZE_FAILED:
            continue
        TextureStat.NO_OF_PIXELS_AFTER += (
            TextureCollection.TEXTURES_TO_BE_PROCESSED[texture]["width"]
            * TextureCollection.TEXTURES_TO_BE_PROCESSED[texture]["height"]
        )

    logger.info(f"{total_texture_modified} textures were modified.")

    if (
        TextureCollection.TEXTURES_TO_BE_PROCESSED.keys()
        and TextureStat.NO_OF_PIXELS_AFTER != 0
    ):
        logger.info(
            f"Total no of pixels before processing -> {TextureStat.NO_OF_PIXELS_BEFORE} px. Total no of pixels after processing -> {TextureStat.NO_OF_PIXELS_AFTER} px"
        )

        logger.info(
            f"Percentage of pixel reduced -> {((TextureStat.NO_OF_PIXELS_BEFORE - TextureStat.NO_OF_PIXELS_AFTER) / TextureStat.NO_OF_PIXELS_BEFORE) * 100} %"
        )

    if TextureCollection.PREPROCESSING_FAILED:
        logger.warning("Following files were failed in pre-processing.")
        for texture in TextureCollection.PREPROCESSING_FAILED:
            logger.warning(texture)

    if TextureCollection.DELETION_FAILED:
        logger.warning("Following .tmp files were not deleted.")
        for texture in TextureCollection.DELETION_FAILED:
            logger.warning(texture)

    if TextureCollection.NUKE_RESIZE_FAILED:
        logger.warning("Following files failed in resizing process.")
        for texture in TextureCollection.NUKE_RESIZE_FAILED:
            logger.warning(texture)


def add_to_perforce(add_to_p4: bool, full_path: Path) -> None:

    change_list_name = (
        f"Textures modified with Texture resizing tool for {full_path.name}."
    )

    if not add_to_p4:
        return

    failed_checkouts = []

    for texture_path in TextureCollection.TEXTURES_TO_BE_PROCESSED:
        logger.info(f"Checking out file : {texture_path}.")
        if client.isCheckedOutByAnyoneElse(texture_path):
            logger.warning(
                f"File {texture_path} is already checked out by a different user."
            )
            failed_checkouts.append(texture_path)
            continue
        if client.isCheckedOut(texture_path):
            logger.info(f"File {texture_path} is already checked out.")
            continue
        client.checkOut(texture_path, description=change_list_name)

    if failed_checkouts:
        output_path = Path(LOG_DIRECTORY, "failed_files.txt").as_posix()
        if os.path.exists(output_path):
            os.remove(output_path)

        with open(output_path, "w") as f:
            f.writelines(failed_checkouts)

        logger.warning(
            f"Some files were failed to checkout. Please find the list of those file in this location -> {output_path}"
        )


def run(full_path: Path, include_sub_dirs: bool, add_to_p4: bool) -> None:

    texture_files = file_helper.get_tif_files(
        full_path.as_posix(), includeSubdirectories=include_sub_dirs
    )

    for texture_file in texture_files:
        file_path = Path(texture_file)
        if file_path.stem in Config.EXCLUSION_LIST:
            logger.info(f"Ignoring excluded file -> {texture_file}")
            continue
        # All hairstyle textures which are not specular textures need to be ignored.
        if "_spec" not in texture_file.lower():
            if any(item in texture_file.lower() for item in Config.ALWAYS_IGNORE):
                logger.info(f"Ignoring hair file -> {texture_file}.")
                continue
        TextureCollection.VALID_TEXTURES_SET.add(file_path)

    if not TextureCollection.VALID_TEXTURES_SET:
        logger.warning("No texture files found.\n")
        return
    else:
        logger.info(f"{len(texture_files)} Texture files found.\n")
        logger.info(
            f"Number of valid textures is {len(TextureCollection.VALID_TEXTURES_SET)}.\n"
        )

    filter_textures()

    process_textures()

    collect_textures_for_downscaling()

    is_succeeded = downscale_textures()

    print_report()

    if not is_succeeded:
        logger.error("Resizing process failed!!")
        return

    add_to_perforce(add_to_p4, full_path)

    logger.info("Texture resizing complete!!")


if __name__ == "__main__":
    cli_main(run)
