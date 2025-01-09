import os
from settings import ROOT_DIR


def get_avatar_image(status: bool | None) -> str:
    """
    Get the path to the appropriate avatar image based on electricity status.

    Args:
        status (bool | None): The electricity status
            - True: electricity is available
            - False: no electricity
            - None: status unknown

    Returns:
        str: Absolute path to the corresponding image file

    Raises:
        KeyError: If status value is not one of: True, False, None
    """
    image_file = {
        None: "LIGHT_UNKNOWN.jpg",
        True: "LIGHT_YES.jpg",
        False: "LIGHT_NO.jpg",
    }
    
    try:
        return os.path.join(ROOT_DIR, "media", image_file[status])
    except KeyError:
        raise KeyError(f"Invalid status value: {status}. Must be True, False, or None")
