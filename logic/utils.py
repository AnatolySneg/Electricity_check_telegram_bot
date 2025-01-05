import os
from settings import ROOT_DIR


def get_avatar_image(status):
    image_file = {
        None: "LIGHT_UNKNOWN.jpg",
        True: "LIGHT_YES.jpg",
        False: "LIGHT_NO.jpg",
    }
    return os.path.join(ROOT_DIR, "media", image_file[status])
