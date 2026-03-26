class GameError(Exception):
    pass


class InvalidTransitionError(GameError):
    pass


class NotFoundError(GameError):
    pass


class NotAuthorizedError(GameError):
    pass


class CostLimitExceededError(GameError):
    pass


# Aliases for backward compatibility
InvalidTransition = InvalidTransitionError
NotFound = NotFoundError
NotAuthorized = NotAuthorizedError
CostLimitExceeded = CostLimitExceededError
