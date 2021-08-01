import json
from hashlib import md5
from os import remove, sep, startfile, system
from os.path import exists

from PIL import Image, UnidentifiedImageError

from dictionaries import read_file_dict
from files import conditional_walk, ignore_dot_dirs
from lists import read_file_lists, write_file_lists
from sets import SetGroup
from tags import get_tags, name_and_ext, set_tags, set_name, add_tags

from math import ceil


def upscale(file: str, min_dim: int = 512, output: str = None) -> str:
    """ returns name of upscaled image, or None if images was not upscaled """
    try:
        img = Image.open(file)
    except (UnidentifiedImageError, PermissionError):
        # probably not an image file
        return None
    if img.width >= min_dim and img.height >= min_dim:
        return None
    scale = ceil(min_dim / min(img.width, img.height))
    scaled_img = img.resize(
        (img.width*scale, img.height*scale), resample=Image.NEAREST)
    if output == None:
        name, ext = name_and_ext(file)
        output = add_tags(set_name(file, f"{name}x{scale}"), {"scaled"})
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
        self.img = Image.open("\\\\?\\"+img_path)
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
        hasher = md5()
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
        full_path = dir+sep+filename
        if self.loaded_from != full_path:
            # if loaded from same file, then this is pointless as it will write the same data back
            with open(dir + sep + filename, "w") as f:
                json.dump({"path": self.path, "horiz": self.horiz_divs,
                           "vert": self.vert_divs, "buckets": self.buckets, "hist": self.section_hists}, f)

    def load_image_data_file(self, dir: str, filename: str = None) -> None:
        if filename == None:
            filename = f"{self.img_hash}.json"
        with open(dir + sep + filename) as f:
            self.loaded_from = dir+sep+filename
            j = json.load(f)
            j_path = j["path"]
            if self.path != j_path:
                if exists(j_path):
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


def find_matches(root: str, similarity_threshold: float, matches_file: str, exact_matches_file: str, saved_data_dir: str = None) -> None:
    # tag -> list of images with that tag
    images_by_tag = {}
    # name -> ImageData
    data = {}

    # the tags that have already been examined; images with only these tags can be unloaded
    matched_tags = set()

    # image name -> set containing it and matching images
    matches = SetGroup()
    exact_matches = SetGroup()

    for dirpath, dirnames, filenames in conditional_walk(root, ignore_dot_dirs):
        for f in filenames:
            tags = get_tags(f)
            if tags == set():
                # compare all images with no tags with each other
                tags = {""}
            for tag in tags:
                path = dirpath + sep + f
                if tag not in images_by_tag:
                    images_by_tag[tag] = []
                images_by_tag[tag].append(path)

    for tag, img_names in images_by_tag.items():
        matched_tags.add(tag)
        not_images = set()
        for name in img_names:
            try:
                try:
                    data[name] = ImageData(
                        name, saved_data_dir)
                except ImageDataPathMismatchException as e:
                    # found a duplicate by exact match
                    exact_matches.join(str(e), name)
                    matches.join(str(e), name)
                    # load from image rather than file for comparison later
                    data[name] = ImageData(name)
                data[name].save_image_data_file(saved_data_dir)
                print("Loaded " + name)
            except UnidentifiedImageError:
                # not an image file, ignore
                not_images.add(name)
                pass
        img_names = [i for i in img_names if i not in not_images]
        for i in range(0, len(img_names) - 1):
            img1 = img_names[i]
            for j in range(i + 1, len(img_names)):
                img2 = img_names[j]

                if img1 in matches and img2 in matches and img1 in matches[img2]:
                    # images already matched together
                    continue

                id1 = data[img1]
                id2 = data[img2]

                #exact_match = id1.exact_match(id2)
                # if not exact_match:
                low_diff = id1.hist_diff_score(id2) <= similarity_threshold

                print("Comparing " + img1 + ", " + img2)

                # if exact_match:
                #    exact_matches.join(img1, img2)

                # if exact_match or low_diff:
                if low_diff:
                    matches.join(img1, img2)
        for name in img_names:
            tags = get_tags(name)
            if tags == set():
                tags = {""}
            if tags - matched_tags == set():
                # if all tags matched, unload image data (no longer needed)
                del data[name]
                print("Unloaded " + name)

    write_file_lists(matches_file, matches.get_all())
    write_file_lists(exact_matches_file, exact_matches.get_all())


def process_matches(matches_file: str, known_matches_file: str) -> None:
    for matches in read_file_lists(matches_file):
        # filter out non-existent files, such as those that have been retagged/renamed
        matches = [f for f in matches if exists(f)]

        while len(matches) > 1:
            for i in range(0, len(matches)):
                img = Image.open(matches[i])
                print(f"{i}: {img.width}x{img.height} {matches[i]}")
                img.close()

            while True:
                str_in = input()
                cmd = str_in.split(" ")

                if len(cmd) == 0:
                    continue

                if cmd[0] == "s" or cmd[0] == "skip":
                    break
                elif cmd[0] == "o" or cmd[0] == "open":
                    if len(cmd) == 1 or cmd[1] == "all":
                        for f in matches:
                            startfile(f)
                    else:
                        try:
                            for i in cmd[1:]:
                                startfile(matches[int(i)])
                        except ValueError:
                            continue
                    continue
                elif cmd[0] == "k" or cmd[0] == "keep":
                    first = True
                    with open(known_matches_file, "a") as kmf:
                        system("taskkill /f /im i_view64.exe")
                        for f in matches:
                            if not exists(f):
                                continue
                            if first:
                                first = False
                            else:
                                kmf.write("|")
                            kmf.write(f)
                        kmf.write("\n")
                    matches = []
                    break
                elif cmd[0] == "d" or cmd[0] == "del" or cmd[0] == "delete":
                    if len(cmd) == 1:
                        continue
                    system("taskkill /f /im Microsoft.Photos.exe")
                    try:
                        delete = int(cmd[1])
                    except ValueError:
                        # try to find string in filename instead
                        delete = 0
                        if cmd[1][0] == "\"":
                            quote1 = str_in.find(
                                "\"")
                            quote2 = str_in.rfind("\"")
                            if quote1 < quote2:
                                del_str = str_in[quote1 + 1:quote2]
                            else:
                                print("unmatched quote")
                                continue
                        else:
                            del_str = cmd[1]
                        for f in matches:
                            if del_str in f:
                                break
                            delete += 1
                    try:
                        remove(matches[delete])
                        print(f"deleted {matches[delete]}")
                        del matches[delete]
                        break
                    except IndexError:
                        continue
