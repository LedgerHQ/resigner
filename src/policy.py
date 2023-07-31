import time

from typing import List, Dict

from .config import Configuration
from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .models import AggregateSpends


class PolicyException(Exception):
    pass


class ImproperlyDefined(PolicyException):
    pass


class Policy():
    def __init__(self, config: Configuration):
        pass

    def has_condition(self, cond: str):
        raise NotImplementedError

    def is_defined(self):
        raise NotImplementedError

    def execute_policy(self):
        raise NotImplementedError


class PolicyHandler:
    __policy_list = []

    def register_policy(self, policy: Policy):
        self.__policy_list.append(policy)

    def run(self, **kwargs):
        for policy in self.__policy_list:
            policy.execute_policy(**kwargs)


class SpendLimit(Policy):
    daily_limit: int
    weekly_limit: int
    monthly_limit: int
    condition: bool = False  # So we fail if policy is not executed

    def __init__(self, btdClient: BitcoindRPC, config: Configuration):
        self._btdClient = btdClient
        self._config = config
    
        # Set limits to zero if not defined
        try:
            spend_cond = config.get("spending_conditions")

            self.daily_limit = spend_cond["daily_limit"] if "daily_limit" in spend_cond else 0
            self.weekly_limit = spend_cond["weekly_limit"] if "weekly_limit" in spend_cond else 0
            self.monthly_limit = spend_cond["monthly_limit"] if "monthly_limit" in spend_cond else 0
        except TypeError:
            pass  # Todo

    def is_defined(self):
        if self.daily_limit or self.weekly_limit or self.monthly_limit:
            return True
        else:
            return False

    def execute_policy(self, **kwargs):

        if self.is_defined():
            aggregate_spend = AggregateSpends.get("daily_spends", "weekly_spends", "monthly_spends")

            if self.daily_limit > 0:
                self.condition = aggregate_spend["daily_spends"] < self.daily_limit and \
                    (aggregate_spend["daily_spends"] + kwargs["amount_sats"]) < self.daily_limit

            if self.weekly_limit > 0:
                self.condition = aggregate_spend["weekly_spends"] < self.weekly_limit and \
                    (aggregate_spend["weekly_spends"] + kwargs["amount_sats"]) < self.weekly_limit

            if self.monthly_limit > 0:
                self.condition = aggregate_spend["monthly_spends"] < self.monthly_limit and \
                    (aggregate_spend["monthly_spends"] + kwargs["amount_sats"]) < self.monthly_limit

        return self.condition

    @property
    def __t_struct(self):
        if not self._config.get("use_servertime"):
            return time.gmtime()
        else:
            return time.gmtime(time.time() - self._config.get("utc_offset"))

    @property
    def _hrs_passed_since_last_day(self):
        return self.__t_struct.tm_hour

    @property
    def _days_passed_since_last_week(self):
        return self.__t_struct.tm_wday + 1

    @property
    def _days_passed_since_last_month(self):
        return self.__t_struct.tm_mday

    """ We are approximating the number of blocks buy using the average number of blocks created in a day.
    This is reasonably fair as the number of blocks created in a day is usually consistent with 144.
    Note: a better approach to determining the number of blocks created since a certain time would be
    to count from the first block with a timestamp after the last period to the best block.
    """
    @property
    def _blocks_created_since_last_day(self):
        return self._hrs_passed_since_last_day * 6

    @property
    def _blocks_created_since_last_week(self):
        return (self.__t_struct.tm_wday + 1) * 144

    @property
    def _blocks_created_since_last_month(self):
        return self.__t_struct.tm_mday * 144


class TFAPolicy(Policy):
    pass
