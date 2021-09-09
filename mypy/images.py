import json
import hashlib
import os
import PIL
import math
from pathlib import Path
from mypy import tags


def upscale(file: str, min_dim: int = 512, output: str = None) -> str:
    """ Returns name of upscaled image which is the original name with the calculated scale factor and with the tag "scaled" added, or None if image was not upscaled """
    try:
        img = PIL.Image.open(file)
    except (PIL.UnidentifiedImageError, PIL.PermissionError):
        # probably not an image file
        return None
    if img.width >= min_dim and img.height >= min_dim:
        return None
    scale = math.ceil(min_dim / min(img.width, img.height))
    scaled_img = img.resize(
        (img.width*scale, img.height*scale), resample=PIL.Image.NEAREST)
    if output == None:
        name, ext = tags.name_and_ext(file)
        output = tags.add_tags(tags.set_name(
            file, f"{name}x{scale}"), {"scaled"})
    scaled_img.save(output)
    return output


class ImageDataComparisonException(Exception):
    pass


class ImageDataLoadException(Exception):
    pass


class ImageDataPathMismatchException(ImageDataLoadException):
    pass


class ImageData:
    def __init__(self, img_path: str, saved_data_dir: str = None, horiz_divs: int = 8, vert_divs: int = 8, buckets: int = 8):
        self.path = img_path
        self.img = PIL.Image.open("\\\\?\\"+img_path)
        if self.img.mode != "RGB":
            self.img = self.img.convert(mode="RGB")
        self.img_hash = self.__img_hash()

        try:
            if saved_data_dir == None:
                raise FileNotFoundError
            self.load_image_data_file(saved_data_dir)
        except FileNotFoundError:
            self.horiz_divs = horiz_divs
            self.vert_divs = vert_divs
            self.buckets = buckets
            self.bucket_size = 256//self.buckets
            self.section_hists = self.__section_hists()
            self.loaded_from = None

    def __combine_buckets(self, hist: list[int]) -> list[int]:
        return [sum(hist[i:i + self.bucket_size]) for i in range(0, len(hist), self.bucket_size)]

    def __normalize_hist(self, hist: list[int]) -> list[int]:
        hsum = sum(hist)
        return [3 * h / hsum for h in hist]

    def __section_hists(self) -> None:
        width = self.img.width
        height = self.img.height
        sect_width = width // self.horiz_divs
        sect_height = height // self.vert_divs

        h_div_bounds = []
        for h in range(0, self.horiz_divs - 1):
            h_div_bounds.append((h * sect_width, (h + 1) * sect_width))
        h_div_bounds.append(((self.horiz_divs - 1) * sect_width, width))

        v_div_bounds = []
        for v in range(0, self.vert_divs - 1):
            v_div_bounds.append((v * sect_height, (v + 1) * sect_height))
        v_div_bounds.append(((self.vert_divs - 1) * sect_height, height))

        hists = []
        for h in h_div_bounds:
            for v in v_div_bounds:
                box = (h[0], v[0],
                       h[1], v[1])
                hists.append(self.img.crop(box).histogram())
        return [self.__normalize_hist(
            self.__combine_buckets(h)) for h in hists]

    def __img_hash(self) -> str:
        hasher = hashlib.md5()
        with open("\\\\?\\"+self.path, "rb") as img_b:
            hasher.update(img_b.read())
        return hasher.hexdigest()

    def hist_diff_score(self, other: "ImageData") -> float:
        if self.horiz_divs != other.horiz_divs or self.vert_divs != other.vert_divs or self.buckets != other.buckets:
            raise ImageDataComparisonException

        # each color in each section can have a difference of up to 2
        max_diff = self.horiz_divs * self.vert_divs * 3 * 2

        diff = 0
        for self_hist, other_hist in zip(self.section_hists, other.section_hists):
            for s, o in zip(self_hist, other_hist):
                diff += abs(s - o)
        # return sum([sum([abs(s-o) for s, o in zip(s_h, o_h)]) for s_h, o_h in zip(self.section_hists, other.section_hists)])
        return diff / max_diff

    def exact_match(self, other: "ImageData") -> bool:
        return self.img_hash == other.img_hash

    def save_image_data_file(self, dir: str, filename: str = None) -> None:
        if filename == None:
            filename = f"{self.img_hash}.json"
        full_path = dir+os.sep+filename
        if self.loaded_from != full_path:
            # if loaded from same file, then this is pointless as it will write the same data back
            with open(dir + os.sep + filename, "w") as f:
                json.dump({"path": self.path, "horiz": self.horiz_divs,
                           "vert": self.vert_divs, "buckets": self.buckets, "hist": self.section_hists}, f)

    def load_image_data_file(self, dir: str, filename: str = None) -> None:
        if filename == None:
            filename = f"{self.img_hash}.json"
        with open(dir + os.sep + filename) as f:
            self.loaded_from = dir+os.sep+filename
            j = json.load(f)
            j_path = j["path"]
            if self.path != j_path:
                if Path(j_path).exists():
                    raise ImageDataPathMismatchException(j_path)
                else:
                    # cause rewrite later if saved to update the path
                    self.loaded_from = None
            self.horiz_divs = j["horiz"]
            self.vert_divs = j["vert"]
            self.buckets = j["buckets"]
            self.bucket_size = 256//self.buckets
            self.section_hists = j["hist"]
            if len(self.section_hists) != self.horiz_divs * self.vert_divs:
                raise ImageDataLoadException(
                    "Mismatch in hist length and number of sections")
            for h in self.section_hists:
                if len(h) != 3 * self.buckets:
                    raise ImageDataLoadException(
                        "Mismatch in number of buckets")
