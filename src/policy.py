import time
from config import Configuration
from bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError



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


class SpendingLimit(Policy):
    daily_limit: int
    weekly_limit: int
    monthly_limit: int

    def __init__(self, btdClient: BitcoindRPC, config: Configuration):
        self._btdClient = btdClient
        self._config = config
        
        if config.get_value("spending_conditions"):
            spend_cond = config.get_value("spending_conditions")
            try:
                self.daily_limit = spend_cond["daily_limit"]
                self.weekly_limit = spend_cond["weekly_limit"]
                self.monthly_limit = spend_cond["monthly_limit"]
            except KeyError:
                pass
        else:
            try:
                self.daily_limit = config.get_value("daily_limit")
                self.weekly_limit = config.get_value("weekly_limit")
                self.monthly_limit = config.get_value("monthly_limit")
            except TypeError:
                pass

    def is_defined(self):
        if self.daily_limit or self.weekly_limit or self.monthly_limit:
            return True
        else:
            return False

    def execute_policy(self):
        block_height = self.btdClient.getblockcount()
        # Calculate no of blocks created since last
        n_blocks_since_last_day = (self._hrs_passed_since_last_day * 60) / 10
        n_blocks_since_last_week = (self._days_passed_since_last_week * 24 * 60) / 10 
        n_blocks_since_last_month = (self._days_passed_since_last_month * 24 * 60) / 10
        pass

    @property
    def __t_struct(self):
        if not self._config.get_value("use_servertime"):
            return time.gmtime()
        else:
            return time.gmtime(time.time() - self._config.get_value("utc_offset"))

    @property
    def _hrs_passed_since_last_day(self):
        return self.__t_struct.tm_hour

    @property
    def _days_passed_since_last_week(self):
        return self.__t_struct.tm_wday + 1

    @property
    def _days_passed_since_last_month(self):
       return self.__t_struct.tm_mday


class TFAPolicy(Policy):
    pass


