from shyft.logger import get_logger

logger = get_logger(__name__)

def display_overview():
    # TODO
    pass

def display_activity(id: str):
    # TODO
    pass

def resolve_pathname(path: str):
    logger.info(f'Resolving pathname "{path}".')
    tokens = path.split('/')[1:]
    if not tokens[0]:
        return display_overview()
    elif tokens[0] == 'activity':
        return display_activity(tokens[1])