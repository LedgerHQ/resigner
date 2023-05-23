from config import Configuration
from typing import TypedDict


class PolicyException(Exception):
    pass


class ImproperlyDefined(PolicyException):
    pass


class Policy(TypedDict):
    def __init__(self, config: Configuration):
        pass

    def has_condition(self, cond: str):
        raise NotImplementedError

    def is_defined(self):
        raise NotImplementedError


class SpendingLimit(Policy):
    daily_limit: int
    weekly_limit: int
    monthly_limit: int

    def __init__(self, config: Configuration):
        self.daily_limit = config.get_condition("daily_limit")
        self.weekly_limit = config.get_condition("weekly_limit")
        self.monthly_limit = config.get_condition("monthly_limit")

    def is_defined(self):
        if self.daily_limit or self.weekly_limit or self.monthly_limit:
            return True
        else:
            return False
