import os
import typing
from pathlib import Path

from PIL import Image


def rgb_diff(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> int:
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    return abs(r1-r2)+abs(g1-g2)+abs(b1-b2)


def image_from_file_or_image(img: typing.Union[os.PathLike, Image.Image]):
    if isinstance(img, os.PathLike) or isinstance(img, str):
        return Image.open(img)
    elif isinstance(img, Image.Image):
        return img
    else:
        raise TypeError


def optional_save(img: Image.Image, output: os.PathLike):
    if output != None:
        output = Path(output)
        img.save(output)


def edge_detect(img: typing.Union[os.PathLike, Image.Image], threshold: int = 60, output: os.PathLike = None):
    with image_from_file_or_image(img).convert(mode="RGB") as img:
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
    optional_save(new, output)
    return new


def scale(img: typing.Union[os.PathLike, Image.Image], scale: float, output: os.PathLike = None) -> str:
    with image_from_file_or_image(img) as img:
        new = img.resize(
            (int(img.width * scale), int(img.height * scale)), resample=Image.BOX)
    optional_save(new, output)
    return new


def resize(img: typing.Union[os.PathLike, Image.Image], size: tuple[int, int], output: os.PathLike = None):
    with image_from_file_or_image(img) as img:
        new = img.resize(size, resample=Image.BOX)
    optional_save(new, output)
    return new
