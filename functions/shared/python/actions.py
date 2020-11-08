class ResourcePending(Exception):
    pass


class ResourceFailed(Exception):
    pass


def take_action(status):
    if status in {'CREATE_PENDING', 'CREATE_IN_PROGRESS', 'UPDATE_PENDING', 'UPDATE_IN_PROGRESS'}:
        raise ResourcePending
    if status != 'ACTIVE':
        raise ResourceFailed
    return True
