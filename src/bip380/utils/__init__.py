import re

REGEX_DERIVATION_PATH = re.compile("^m(/[0-9]+['hH]?)*$")
HARDENED_INDEX = 0x80000000
ENCODING_PREFIX = {
    "main": {
        "private": 0x0488ADE4,
        "public": 0x0488B21E,
    },
    "test": {
        "private": 0x04358394,
        "public": 0x043587CF,
    },
}

def _deriv_path_str_to_list(strpath):
    """Converts a derivation path as string to a list of integers
       (index of each depth)

    :param strpath: Derivation path as string with "m/x/x'/x" notation.
                    (e.g. m/0'/1/2'/2 or m/0H/1/2H/2 or m/0h/1/2h/2)

    :return: Derivation path as a list of integers (index of each depth)
    """
    if not REGEX_DERIVATION_PATH.match(strpath):
        raise ValueError("invalid format")
    indexes = strpath.split("/")[1:]
    list_path = []
    for i in indexes:
        # if HARDENED
        if i[-1:] in ["'", "h", "H"]:
            list_path.append(int(i[:-1]) + HARDENED_INDEX)
        else:
            list_path.append(int(i))
    return list_path