import datetime
from copy import deepcopy

from freqtrade.persistence import Order
from freqtrade.persistence.models import init_db


def _mk_order():
    now = datetime.datetime.now(datetime.timezone.utc)
    return Order(
        order_id="1", ft_order_side="buy", ft_pair="BTC/USDT:USDT", ft_is_open=False,
        order_type="limit", side="buy", price=100.0, average=100.0, amount=1.0,
        filled=1.0, remaining=0.0, cost=100.0, status="closed", symbol="BTC/USDT:USDT",
        order_date=now, order_filled_date=now, ft_amount=1.0, ft_price=100.0,
    )


def test_order_deepcopy_value_equal_and_independent():
    init_db("sqlite://")
    o = _mk_order()
    c = deepcopy(o)
    # value-equal on strategy-visible fields
    assert (c.price, c.amount, c.ft_order_side, c.status) == (100.0, 1.0, "buy", "closed")
    # writable (protective copy must accept mutation)
    c.price = 999.0
    c.status = "canceled"
    # independent: original untouched
    assert o.price == 100.0 and o.status == "closed"
    assert c.price == 999.0 and c.status == "canceled"


def test_wrapper_copy_shields_original_trade():
    from freqtrade.strategy.strategy_wrapper import strategy_safe_wrapper

    init_db("sqlite://")
    order = _mk_order()

    class _Trade:  # minimal stand-in with an orders list + scalar the callback mutates
        def __init__(self):
            self.stop_loss = 1.0
            self.orders = [order]

    real = _Trade()

    def mutating_callback(*, trade):
        trade.stop_loss = 0.0  # scalar mutation
        trade.orders[0].price = 1.0  # nested Order mutation
        return "mutated"

    # non-IStrategy qualname => wrapper deep-copies the trade kwarg
    mutating_callback.__qualname__ = "UserStrategy.mutating_callback"
    out = strategy_safe_wrapper(mutating_callback)(trade=real)

    assert out == "mutated"
    assert real.stop_loss == 1.0  # original scalar untouched
    assert real.orders[0].price == 100.0  # original nested Order untouched
