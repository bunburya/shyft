from typing import List


def id_str_to_ints(id_str: str) -> List[int]:
    """Convert a string containing comma-separated activity IDs to a
    list of integers, performing some basic verification and raising a
    ValueError if one of the given IDs is not valid.
    """
    id_list = id_str.split(',')
    int_ids = []
    for i in id_list:
        try:
            int_ids.append(int(i))
        except (ValueError, TypeError):
            raise ValueError(f'Bad activity id: "{i}".')
    return int_ids