from helpers.time_utils import days, hours
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett, settTestConfig
from tests.helpers import distribute_from_whales, getTokenMetadata
from tests.test_recorder import EventRecord, TestRecorder
from rich.console import Console

console = Console()


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settConfig",
    settTestConfig,
)
def test_single_user_harvest_flow(settConfig):
    badger = badger_single_sett(settConfig)
    depositAmount = 50 * 1e8  # renBTC decimal is 8

    # test settings
    controller = badger.getController(settConfig["id"])
    sett = badger.getSett(settConfig["id"])
    strategy = badger.getStrategy(settConfig["id"])
    want = badger.getStrategyWant(settConfig["id"])
    deployer = badger.deployer

    # production settings
    # controller = interface.IController("0x9b4efa18c0c6b4822225b81d150f3518160f8609");
    # sett = interface.ISett("0x77f07Dd580cc957109c70c7fa81aa5704f8a3572")
    # strategy = StrategyUnitProtocolRenbtc.at("0x5640d6E2F72e76FBCb5296d59EA28C7375F1fE12");
    # want = interface.IERC20("0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D")
    # deployer = accounts.at("0x576cD258835C529B54722F84Bb7d4170aA932C64", force=True)
    # controllerGov = accounts.at("0xB65cef03b9B89f99517643226d76e286ee999e77", force=True)
    # ethWhale = accounts.at("0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE", force=True)
    # ethWhale.transfer(deployer, "100 ether")
    # settGuestList = interface.IVipCappedGuestList("0x9FC48e61B6a75eE263ca160aCF3288A99238719E");
    # settGuestList.setGuests([deployer], [True], {"from": deployer});
    # settGuestList.setUserDepositCap(depositAmount * 2, {"from": deployer});
    # settGuestList.setTotalDepositCap(depositAmount * 10, {"from": deployer});
    # controller.setVault(want, sett, {"from": deployer});
    # controller.approveStrategy(want, strategy, {"from": controllerGov});
    # controller.setStrategy(want, strategy, {"from": deployer});

    settKeeper = accounts.at(sett.keeper(), force=True)
    strategyKeeper = accounts.at(strategy.keeper(), force=True)

    snap = SnapshotManager(badger, settConfig["id"])

    governance = strategy.governance()

    tendable = strategy.isTendable()

    distribute_from_whales(deployer)
    startingBalance = want.balanceOf(deployer)

    assert startingBalance >= depositAmount
    assert startingBalance >= 0

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    # sett.deposit(depositAmount, {"from": deployer});
    snap.settDeposit(depositAmount, {"from": deployer})

    assert want.balanceOf(sett) > 0
    print("want.balanceOf(sett)", want.balanceOf(sett))

    # Earn
    # sett.earn({"from": settKeeper});
    snap.settEarn({"from": settKeeper})

    # Harvest
    chain.sleep(hours(0.1))
    chain.mine()
    # strategy.harvest({"from": strategyKeeper})
    snap.settHarvest({"from": strategyKeeper})

    # Withdraw half
    # sett.withdraw(depositAmount // 2, {"from": deployer})
    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    # KeepMinRatio to maintain collateralization safe enough from liquidation
    currentRatio = strategy.currentRatio()
    safeRatio = currentRatio + 20
    strategy.setMinRatio(safeRatio, {"from": governance})
    strategy.keepMinRatio({"from": governance})
    assert strategy.currentRatio() > safeRatio

    # sugar-daddy usdp discrepancy due to accrued interest in Unit Protocol
    debtTotal = strategy.getDebtBalance()
    curveGauge = interface.ICurveGauge("0x055be5DDB7A925BfEF3417FC157f53CA77cA7222")
    usdp3crvInGauge = curveGauge.balanceOf(strategy)
    curvePool = interface.ICurveFi("0x42d7025938bEc20B69cBae5A77421082407f053A")
    usdpOfPool = curvePool.calc_withdraw_one_coin(usdp3crvInGauge, 0)
    sugar = (debtTotal - usdpOfPool) * 2
    usdpToken = interface.IERC20("0x1456688345527bE1f37E9e627DA0837D6f08C925")
    if sugar > 0:
        usdpToken.transfer(strategy, sugar, {"from": deployer})
        print("sugar debt=", sugar)

    # Harvest again
    chain.sleep(hours(0.1))
    chain.mine()
    # strategy.harvest({"from": strategyKeeper})
    snap.settHarvest({"from": strategyKeeper})

    # Withdraw all
    wantInSettBalance = sett.getPricePerFullShare() * sett.totalSupply() / 1e18
    print("wantInSett=", wantInSettBalance)
    print("wantInStrategy=", strategy.balanceOfPool())
    print("pricePerFullShare=", sett.getPricePerFullShare())
    wantToWithdraw = sett.balanceOf(deployer) * sett.getPricePerFullShare() / 1e18
    print("wantToWithdraw=", wantToWithdraw)
    assert wantToWithdraw <= wantInSettBalance

    sugarWithdrawAll = (strategy.getDebtBalance() - strategy.balanceOfPool()) * 2
    if sugarWithdrawAll > 0:
        usdpToken.transfer(strategy, sugarWithdrawAll, {"from": deployer})
        print("sugarWithdrawAll=", sugarWithdrawAll)

    renbtcToken = interface.IERC20("0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D")
    controller.withdrawAll(renbtcToken, {"from": deployer})

    # sett.withdrawAll({"from": deployer})
    snap.settWithdrawAll({"from": deployer})

    assert True
