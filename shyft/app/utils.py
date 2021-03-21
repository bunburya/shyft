from typing import List


def id_str_to_ints(ids: str) -> List[int]:
    """Convert a string containing comma-separated activity IDs to a
    list of integers, performing some basic verification and raising a
    ValueError if one of the given IDs is not valid.
    """
    ids = ids.split(',')
    int_ids = []
    for i in ids:
        try:
            int_ids.append(int(i))
        except (ValueError, TypeError):
            raise ValueError(f'Bad activity id: "{i}".')
    return int_ids