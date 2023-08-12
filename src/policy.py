import time

from typing import List, Dict, Optional

from .config import Configuration
from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .models import AggregateSpends
from .analysis import ResignerPsbt


class PolicyException(Exception):
    def __init__(self, message):
        self.message = message


class Policy():
    def has_condition(self, cond: str):
        raise NotImplementedError

    def is_defined(self):
        raise NotImplementedError

    def execute_policy(self):
        raise NotImplementedError


class PolicyHandler:
    __policy_list = []

    def register_policy(self, policy: List[Policy]):
        self.__policy_list.append(*policy)

    def run(self, psbt: Optional[ResignerPsbt] = None, **kwargs):
        if psbt is None:
            raise TypeError("psbt must not be None")
        for policy in self.__policy_list:
            if policy.is_defined:
                if not policy.execute_policy(psbt=psbt, **kwargs):
                    raise PolicyException(f"Failed while executing {policy._name} policy")

class SpendLimit(Policy):
    _name: str = "SpendLimit"
    daily_limit: int
    weekly_limit: int
    monthly_limit: int
    condition: bool = False  # So we fail if policy is not executed

    def __init__(self, config: Configuration):
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

    def execute_policy(self, psbt: ResignerPsbt, **kwargs):
        psbt=psbt["psbt"]

        if self.is_defined():
            aggregate_spend = AggregateSpends.get(
                ["confirmed_daily_spends", "confirmed_weekly_spends", "confirmed_monthly_spends"]
            )[0]

            print("aggregate_spend: ", aggregate_spend)

            if self.daily_limit > 0:
                self.condition = (aggregate_spend["confirmed_daily_spends"] < self.daily_limit and
                    (aggregate_spend["confirmed_daily_spends"] + psbt.amount_sats) < self.daily_limit)

            if self.weekly_limit > 0:
                self.condition = (aggregate_spend["confirmed_weekly_spends"] < self.weekly_limit and
                    (aggregate_spend["confirmed_weekly_spends"] + psbt.amount_sats) < self.weekly_limit)

            if self.monthly_limit > 0:
                self.condition = (aggregate_spend["confirmed_monthly_spends"] < self.monthly_limit and
                    (aggregate_spend["confirmed_monthly_spends"] + psbt.amount_sats) < self.monthly_limit)

        return self.condition

    @property
    def __t_struct(self):
        if "use_servertime" not in self._config.get("resigner_config"):
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

    # We are approximating the number of blocks buy using the average number of blocks created in a day.
    # This is reasonably fair as the number of blocks created in a day is usually consistent with 144.
    # Note: a better approach to determining the number of blocks created since a certain time would be
    # to count from the first block with a timestamp after the last period to the best block.
    
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
