from helpers.snapshot import diff_numbers_by_key, snap_strategy_balance
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.sushiswap_system import SushiswapSystem

from helpers.utils import shares_to_fragments, to_digg_shares, to_tabulate, tx_wait
from helpers.sett.SnapshotManager import SnapshotManager
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from assistant.rewards.rewards_checker import val
from helpers.console_utils import console
from config.active_emissions import active_emissions, get_daily_amount, get_half_daily_amount

gas_strategy = GasNowStrategy("fast")

uniswap = UniswapSystem()
sushiswap = SushiswapSystem()

def transfer_for_strategy(badger: BadgerSystem, key, amount, decimals=18):
    console.print("Transferring Amount for Strategy {}".format(key), val(amount, decimals))
    manager = badger.badgerRewardsManager
    strategy = badger.getStrategy(key)

    before = snap_strategy_balance(badger, key, manager)

    transfer_for_strategy_internal(badger, key, amount)

    after = snap_strategy_balance(badger, key, manager)
    diff = diff_numbers_by_key(before, after)

    console.print("[green]==Transfer for {}==[/green]".format(key))
    to_tabulate("Diff {}".format(key), diff)

def transfer_for_strategy_internal(badger, key, amount):
    digg = badger.digg
    strategy = badger.getStrategy(key)
    manager = badger.badgerRewardsManager
    want = interface.IERC20(strategy.want())
    manager.transferWant(want, strategy, amount, {"from": badger.keeper})

def rapid_harvest():
    """
    Atomically transfer and deposit tokens from rewards manager to associated strategies
    Requires that LP positons are swapped
    """

    # TODO: Output message when failure
    # TODO: Use test mode if RPC active, no otherwise

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName, load_keeper=True)
    digg = badger.digg
    manager = badger.badgerRewardsManager

    if rpc.is_active():
        """
        Test: Load up sending accounts with ETH and whale tokens
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    # TODO: Daily amount = calculate from the LP token scale

    # # # ===== native.uniBadgerWbtc =====
    key = "native.uniBadgerWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.sushiBadgerWbtc =====
    key = "native.sushiBadgerWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.uniDiggWbtc =====
    key = "native.uniDiggWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # # # ===== native.sushiDiggWbtc =====
    key = "native.sushiDiggWbtc"
    want = badger.getStrategyWant(key)
    transfer_for_strategy(badger, key, want.balanceOf(manager))

    # ===== native.badger =====
    key = "native.badger"
    # TODO: Specify actual amounts here
    transfer_for_strategy(badger, key, get_daily_amount(key, "badger"))

    # ===== native.digg =====
    key = "native.digg"
    transfer_for_strategy(badger, key, get_daily_amount(key, "digg"), decimals=9)

def main():
    rapid_harvest()