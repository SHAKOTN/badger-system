from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StabilizeStrategyDiggV1Resolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after, tx):
        # No-op, nothing to harvest - rewards are handled externally.
        pass

    def get_strategy_destinations(self):
        return {}