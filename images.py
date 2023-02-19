import hashlib
import os
import random
import typing
from pathlib import Path

from PIL import Image


def rgb_diff(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> int:
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    return abs(r1-r2)+abs(g1-g2)+abs(b1-b2)


def _image_from_file_or_image(img: typing.Union[os.PathLike, Image.Image]):
    if isinstance(img, os.PathLike) or isinstance(img, str):
        return Image.open(img)
    elif isinstance(img, Image.Image):
        return img
    else:
        raise TypeError


def _optional_save(img: Image.Image, output: os.PathLike):
    if output != None:
        output = Path(output)
        img.save(output)


def edge_detect(img: typing.Union[os.PathLike, Image.Image], threshold: int = 60, output: os.PathLike = None):
    with _image_from_file_or_image(img).convert(mode="RGB") as img:
        new = Image.new("RGB", img.size)
        for x in range(1, img.width):
            for y in range(1, img.height):
                current = img.getpixel((x, y))
                neighbors = [img.getpixel(
                    (x-1, y)), img.getpixel((x-1, y-1)), img.getpixel((x, y-1))]
                if not x == img.width - 1:
                    neighbors.append(img.getpixel((x+1, y-1)))
                for n in neighbors:
                    if rgb_diff(current, n) > threshold:
                        new.putpixel((x, y), (255, 255, 255))
                        break
    _optional_save(new, output)
    return new


def scale(img: typing.Union[os.PathLike, Image.Image], scale: float, output: os.PathLike = None) -> str:
    with _image_from_file_or_image(img) as img:
        new = img.resize(
            (int(img.width * scale), int(img.height * scale)), resample=Image.BOX)
    _optional_save(new, output)
    return new


def resize(img: typing.Union[os.PathLike, Image.Image], size: tuple[int, int], output: os.PathLike = None):
    with _image_from_file_or_image(img) as img:
        new = img.resize(size, resample=Image.BOX)
    _optional_save(new, output)
    return new


def rgb_image_diff(img1: typing.Union[os.PathLike, Image.Image], img2: typing.Union[os.PathLike, Image.Image]) -> tuple[int, int]:
    """Returns a pair of ints. The first is the total RGB difference (each pixel pair's difference is always given as the absolute value). The second is the maximum possible RGB difference given the size of the images (which must be the same)."""
    with _image_from_file_or_image(img1).convert(mode="RGB") as img1:
        with _image_from_file_or_image(img2).convert(mode="RGB") as img2:
            if img1.size != img2.size:
                raise TypeError
            width, height = img1.size
            sum = 0
            for x in range(0, width):
                for y in range(0, height):
                    sum += rgb_diff(img1.getpixel((x, y)),
                                    img2.getpixel((x, y)))
    # maximum difference is 255 per color per pixel (e.g. an all-white image and an all-black image)
    return sum, 765*width*height


def collage(imgs: list[typing.Union[os.PathLike, Image.Image]], width: int, height: int, img_width: int, img_height: int, shuffle: bool = False, output: os.PathLike = None):
    """Make a collage of a list of images which must all be scaled to the same dimensions."""

    len_imgs = len(imgs)
    if len_imgs > width*height:
        raise Exception(
            f"Number of images ({len_imgs}) exceeds width*height ({width*height})")

    imgs = [_image_from_file_or_image(i) for i in imgs]

    if shuffle:
        random.shuffle(imgs)

    new = Image.new("RGB", (img_width * width, img_height * height))

    for index in range(0, len_imgs):
        img = resize(imgs[index], (img_width, img_height))
        if img.size != (img_width, img_height):
            raise Exception(
                f"Current image size {(img.size)} differs from first image size {(img_width,img_height)})")

        row = index // width
        col = index % width

        new.paste(img, (col * img_width, row * img_height))

    _optional_save(new, output)
    return new


def hash(img: typing.Union[os.PathLike, Image.Image], *, hash_function: str = "MD5", hex: bool = True) -> int:
    """ Hash with the specified function (default MD5). Uses PIL to ignore image metadata. """
    img = _image_from_file_or_image(img)
    h = hashlib.new(hash_function, img.tobytes(), usedforsecurity=False)
    return h.hexdigest() if hex else h.digest()
