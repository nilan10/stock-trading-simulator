import unittest
from contextlib import contextmanager
from decimal import Decimal

from flask import session
from werkzeug.security import generate_password_hash

from app import app
from models.models import (
    db,
    User,
    Stock,
    Portfolio,
    Order,
    GameState
)

from services.market_order_service import (
    get_market_fee_percent,
    calculate_market_fee,
    buy_stock,
    sell_stock,
    get_open_market_orders,
    execute_market_buy,
    execute_market_sell
)

from services.user_order_service import (
    create_user_order,
    get_open_orders,
    update_user_order,
    cancel_user_order,
    accept_user_order
)


class TestOrderModule(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        with app.app_context():
            db.create_all()

            game_state = GameState(
                current_round=1,
                time_remaining=60,
                status="ACTIVE",
                starting_capital=100000.00,
                market_fee_percent=5.00
            )

            trader = User(
                username="trader",
                password_hash=generate_password_hash("password"),
                role="Trader",
                cash_balance=100000.00,
                reserved_cash=0.00
            )

            seller = User(
                username="seller",
                password_hash=generate_password_hash("password"),
                role="Trader",
                cash_balance=100000.00,
                reserved_cash=0.00
            )

            buyer = User(
                username="buyer",
                password_hash=generate_password_hash("password"),
                role="Trader",
                cash_balance=100000.00,
                reserved_cash=0.00
            )

            other_user = User(
                username="other",
                password_hash=generate_password_hash("password"),
                role="Trader",
                cash_balance=100000.00,
                reserved_cash=0.00
            )

            stock = Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.00,
                total_supply=1000,
                available_supply=1000,
                volatility=5.00
            )

            db.session.add_all([
                game_state,
                trader,
                seller,
                buyer,
                other_user,
                stock
            ])

            db.session.commit()

            self.trader_id = trader.id
            self.seller_id = seller.id
            self.buyer_id = buyer.id
            self.other_user_id = other_user.id
            self.stock_id = stock.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    @contextmanager
    def logged_in(self, user_id):
        with app.test_request_context():
            session["user_id"] = user_id
            yield

    def create_portfolio(
        self,
        user_id,
        quantity,
        reserved_quantity=0,
        avg_buy_price=150.00
    ):
        with app.app_context():
            portfolio = Portfolio(
                user_id=user_id,
                stock_id=self.stock_id,
                quantity=quantity,
                reserved_quantity=reserved_quantity,
                avg_buy_price=avg_buy_price
            )

            db.session.add(portfolio)
            db.session.commit()

    # ---------------------------------------------------------
    # MARKET FEE
    # ---------------------------------------------------------

    def test_get_market_fee_percent(self):
        with app.app_context():
            self.assertEqual(
                get_market_fee_percent(),
                Decimal("5.00")
            )

    def test_calculate_market_fee(self):
        with app.app_context():
            self.assertEqual(
                calculate_market_fee(300),
                Decimal("15.00")
            )

    def test_market_fee_default(self):
        with app.app_context():
            GameState.query.delete()
            db.session.commit()

            self.assertEqual(
                get_market_fee_percent(),
                Decimal("5.00")
            )

    # ---------------------------------------------------------
    # MARKET BUY
    # ---------------------------------------------------------

    def test_buy_stock_requires_login(self):
        with app.test_request_context():
            success, message = buy_stock("AAPL", 1)

            self.assertFalse(success)
            self.assertEqual(message, "You must be logged in.")

    def test_buy_stock_success(self):
        with self.logged_in(self.trader_id):
            success, message = buy_stock("AAPL", 2)

            self.assertTrue(success)

            order = Order.query.first()
            user = db.session.get(User, self.trader_id)

            self.assertEqual(order.order_type, "BUY")
            self.assertEqual(order.order_source, "MARKET")
            self.assertEqual(order.quantity, 2)
            self.assertEqual(order.status, "OPEN")

            self.assertEqual(
                Decimal(str(order.market_fee)),
                Decimal("15.00")
            )

            self.assertEqual(
                Decimal(str(user.reserved_cash)),
                Decimal("315.00")
            )

    def test_buy_stock_invalid_quantity(self):
        with self.logged_in(self.trader_id):
            success, message = buy_stock("AAPL", 0)

            self.assertFalse(success)
            self.assertEqual(
                message,
                "Quantity must be a positive whole number."
            )

    def test_buy_stock_invalid_ticker(self):
        with self.logged_in(self.trader_id):
            success, message = buy_stock("FAKE", 1)

            self.assertFalse(success)
            self.assertEqual(message, "Stock not found.")

    def test_buy_stock_insufficient_supply(self):
        with app.app_context():
            stock = db.session.get(Stock, self.stock_id)
            stock.available_supply = 1
            db.session.commit()

        with self.logged_in(self.trader_id):
            success, message = buy_stock("AAPL", 2)

            self.assertFalse(success)
            self.assertEqual(
                message,
                "Not enough shares available."
            )

    def test_buy_stock_insufficient_cash(self):
        with app.app_context():
            user = db.session.get(User, self.trader_id)
            user.cash_balance = 100
            db.session.commit()

        with self.logged_in(self.trader_id):
            success, message = buy_stock("AAPL", 1)

            self.assertFalse(success)
            self.assertEqual(
                message,
                "Insufficient available funds."
            )

    # ---------------------------------------------------------
    # MARKET SELL
    # ---------------------------------------------------------

    def test_sell_stock_requires_login(self):
        with app.test_request_context():
            success, message = sell_stock("AAPL", 1)

            self.assertFalse(success)
            self.assertEqual(message, "You must be logged in.")

    def test_sell_stock_success(self):
        self.create_portfolio(self.trader_id, 10)

        with self.logged_in(self.trader_id):
            success, message = sell_stock("AAPL", 3)

            self.assertTrue(success)

            order = Order.query.first()
            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(order.order_type, "SELL")
            self.assertEqual(order.order_source, "MARKET")
            self.assertEqual(order.quantity, 3)
            self.assertEqual(order.status, "OPEN")
            self.assertEqual(portfolio.reserved_quantity, 3)

    def test_sell_stock_without_portfolio(self):
        with self.logged_in(self.trader_id):
            success, message = sell_stock("AAPL", 1)

            self.assertFalse(success)
            self.assertEqual(
                message,
                "You do not own enough shares."
            )

    def test_sell_stock_insufficient_shares(self):
        self.create_portfolio(self.trader_id, 5)

        with self.logged_in(self.trader_id):
            success, message = sell_stock("AAPL", 6)

            self.assertFalse(success)

    # ---------------------------------------------------------
    # MARKET ORDER RETRIEVAL
    # ---------------------------------------------------------

    def test_get_open_market_orders(self):
        with self.logged_in(self.trader_id):
            buy_stock("AAPL", 1)
            orders = get_open_market_orders()

            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0].order_source, "MARKET")
            self.assertEqual(orders[0].status, "OPEN")

    # ---------------------------------------------------------
    # EXECUTE MARKET BUY
    # ---------------------------------------------------------

    def test_execute_market_buy(self):
        with self.logged_in(self.trader_id):
            buy_stock("AAPL", 2)
            order_id = Order.query.first().id

        with app.app_context():
            order = db.session.get(Order, order_id)

            success, message = execute_market_buy(order)

            self.assertTrue(success)

            user = db.session.get(User, self.trader_id)
            stock = db.session.get(Stock, self.stock_id)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(
                Decimal(str(user.cash_balance)),
                Decimal("99685.00")
            )
            self.assertEqual(
                Decimal(str(user.reserved_cash)),
                Decimal("0.00")
            )
            self.assertEqual(stock.available_supply, 998)
            self.assertEqual(portfolio.quantity, 2)
            self.assertEqual(order.status, "EXECUTED")

    def test_execute_market_buy_insufficient_supply(self):
        with self.logged_in(self.trader_id):
            buy_stock("AAPL", 2)
            order_id = Order.query.first().id

        with app.app_context():
            stock = db.session.get(Stock, self.stock_id)
            stock.available_supply = 1
            db.session.commit()

            order = db.session.get(Order, order_id)

            success, message = execute_market_buy(order)

            self.assertFalse(success)

    # ---------------------------------------------------------
    # EXECUTE MARKET SELL
    # ---------------------------------------------------------

    def test_execute_market_sell(self):
        self.create_portfolio(self.trader_id, 10)

        with self.logged_in(self.trader_id):
            sell_stock("AAPL", 3)
            order_id = Order.query.first().id

        with app.app_context():
            order = db.session.get(Order, order_id)

            success, message = execute_market_sell(order)

            self.assertTrue(success)

            user = db.session.get(User, self.trader_id)
            stock = db.session.get(Stock, self.stock_id)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(
                Decimal(str(user.cash_balance)),
                Decimal("100427.50")
            )
            self.assertEqual(portfolio.quantity, 7)
            self.assertEqual(portfolio.reserved_quantity, 0)
            self.assertEqual(stock.available_supply, 1003)
            self.assertEqual(order.status, "EXECUTED")

    def test_execute_market_sell_removes_empty_portfolio(self):
        self.create_portfolio(
            self.trader_id,
            2,
            reserved_quantity=0
        )

        with self.logged_in(self.trader_id):
            success, message = sell_stock("AAPL", 2)

            self.assertTrue(success)

            order_id = Order.query.first().id

        with app.app_context():
            order = db.session.get(Order, order_id)

            success, message = execute_market_sell(order)

            self.assertTrue(success)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertIsNone(portfolio)

    # ---------------------------------------------------------
    # PLAYER ORDERS
    # ---------------------------------------------------------

    def test_create_user_buy_order(self):
        with self.logged_in(self.trader_id):
            success, message, order = create_user_order(
                "AAPL",
                "BUY",
                2,
                Decimal("140.00")
            )

            self.assertTrue(success)
            self.assertEqual(order.order_type, "BUY")
            self.assertEqual(order.order_source, "PLAYER")
            self.assertEqual(order.quantity, 2)

            user = db.session.get(User, self.trader_id)

            self.assertEqual(
                Decimal(str(user.reserved_cash)),
                Decimal("280.00")
            )

    def test_create_user_sell_order(self):
        self.create_portfolio(self.trader_id, 10)

        with self.logged_in(self.trader_id):
            success, message, order = create_user_order(
                "AAPL",
                "SELL",
                3,
                Decimal("160.00")
            )

            self.assertTrue(success)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(portfolio.reserved_quantity, 3)

    def test_create_user_order_requires_login(self):
        with app.test_request_context():
            success, message, order = create_user_order(
                "AAPL",
                "BUY",
                1,
                Decimal("150.00")
            )

            self.assertFalse(success)
            self.assertIsNone(order)

    def test_create_user_order_invalid_type(self):
        with self.logged_in(self.trader_id):
            success, message, order = create_user_order(
                "AAPL",
                "INVALID",
                1,
                Decimal("150.00")
            )

            self.assertFalse(success)
            self.assertIsNone(order)

    def test_create_user_order_insufficient_cash(self):
        with app.app_context():
            user = db.session.get(User, self.trader_id)
            user.cash_balance = 100
            db.session.commit()

        with self.logged_in(self.trader_id):
            success, message, order = create_user_order(
                "AAPL",
                "BUY",
                1,
                Decimal("150.00")
            )

            self.assertFalse(success)

    def test_create_user_order_insufficient_shares(self):
        self.create_portfolio(self.trader_id, 2)

        with self.logged_in(self.trader_id):
            success, message, order = create_user_order(
                "AAPL",
                "SELL",
                3,
                Decimal("150.00")
            )

            self.assertFalse(success)

    # ---------------------------------------------------------
    # GET PLAYER ORDERS
    # ---------------------------------------------------------

    def test_get_open_orders(self):
        with self.logged_in(self.trader_id):
            create_user_order(
                "AAPL",
                "BUY",
                2,
                Decimal("140.00")
            )

            orders = get_open_orders()

            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0]["ticker"], "AAPL")
            self.assertEqual(orders[0]["order_type"], "BUY")
            self.assertEqual(orders[0]["quantity"], 2)
            self.assertEqual(orders[0]["status"], "OPEN")

    # ---------------------------------------------------------
    # UPDATE PLAYER ORDERS
    # ---------------------------------------------------------

    def test_update_buy_order(self):
        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                2,
                Decimal("140.00")
            )

            order_id = order.id

            success, message = update_user_order(
                order_id,
                3,
                Decimal("150.00")
            )

            self.assertTrue(success)

            updated_order = db.session.get(Order, order_id)

            self.assertEqual(updated_order.quantity, 3)
            self.assertEqual(
                Decimal(str(updated_order.price)),
                Decimal("150.00")
            )

    def test_update_sell_order(self):
        self.create_portfolio(self.trader_id, 10)

        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "SELL",
                2,
                Decimal("140.00")
            )

            order_id = order.id

            success, message = update_user_order(
                order_id,
                4,
                Decimal("150.00")
            )

            self.assertTrue(success)

            updated_order = db.session.get(Order, order_id)

            self.assertEqual(updated_order.quantity, 4)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(portfolio.reserved_quantity, 4)

    def test_update_order_rejects_non_owner(self):
        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                1,
                Decimal("140.00")
            )

            order_id = order.id

        with self.logged_in(self.other_user_id):
            success, message = update_user_order(
                order_id,
                2,
                Decimal("150.00")
            )

            self.assertFalse(success)

    # ---------------------------------------------------------
    # CANCEL PLAYER ORDERS
    # ---------------------------------------------------------

    def test_cancel_buy_order(self):
        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                2,
                Decimal("140.00")
            )

            order_id = order.id

            success, message = cancel_user_order(order_id)

            self.assertTrue(success)

            user = db.session.get(User, self.trader_id)
            cancelled = db.session.get(Order, order_id)

            self.assertEqual(
                Decimal(str(user.reserved_cash)),
                Decimal("0.00")
            )
            self.assertEqual(cancelled.status, "CANCELLED")

    def test_cancel_sell_order(self):
        self.create_portfolio(self.trader_id, 10)

        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "SELL",
                3,
                Decimal("150.00")
            )

            order_id = order.id

            success, message = cancel_user_order(order_id)

            self.assertTrue(success)

            portfolio = Portfolio.query.filter_by(
                user_id=self.trader_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(portfolio.reserved_quantity, 0)

    def test_cancel_order_rejects_non_owner(self):
        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                1,
                Decimal("140.00")
            )

            order_id = order.id

        with self.logged_in(self.other_user_id):
            success, message = cancel_user_order(order_id)

            self.assertFalse(success)

    # ---------------------------------------------------------
    # ACCEPT SELL ORDER
    # ---------------------------------------------------------

    def test_accept_sell_order(self):
        self.create_portfolio(self.seller_id, 10)

        with self.logged_in(self.seller_id):
            _, _, order = create_user_order(
                "AAPL",
                "SELL",
                3,
                Decimal("140.00")
            )

            order_id = order.id

        with self.logged_in(self.buyer_id):
            success, message = accept_user_order(order_id)

            self.assertTrue(success)

        with app.app_context():
            seller_portfolio = Portfolio.query.filter_by(
                user_id=self.seller_id,
                stock_id=self.stock_id
            ).first()

            buyer_portfolio = Portfolio.query.filter_by(
                user_id=self.buyer_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(seller_portfolio.quantity, 7)
            self.assertEqual(buyer_portfolio.quantity, 3)

            order = db.session.get(Order, order_id)
            self.assertEqual(order.status, "EXECUTED")

    # ---------------------------------------------------------
    # ACCEPT BUY ORDER
    # ---------------------------------------------------------

    def test_accept_buy_order(self):
        self.create_portfolio(self.seller_id, 10)

        with self.logged_in(self.buyer_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                3,
                Decimal("140.00")
            )

            order_id = order.id

        with self.logged_in(self.seller_id):
            success, message = accept_user_order(order_id)

            self.assertTrue(success)

        with app.app_context():
            seller_portfolio = Portfolio.query.filter_by(
                user_id=self.seller_id,
                stock_id=self.stock_id
            ).first()

            buyer_portfolio = Portfolio.query.filter_by(
                user_id=self.buyer_id,
                stock_id=self.stock_id
            ).first()

            self.assertEqual(seller_portfolio.quantity, 7)
            self.assertEqual(buyer_portfolio.quantity, 3)

            buyer = db.session.get(User, self.buyer_id)

            self.assertEqual(
                Decimal(str(buyer.reserved_cash)),
                Decimal("0.00")
            )

            order = db.session.get(Order, order_id)
            self.assertEqual(order.status, "EXECUTED")

    # ---------------------------------------------------------
    # ACCEPT ORDER VALIDATION
    # ---------------------------------------------------------

    def test_accept_own_order_rejected(self):
        with self.logged_in(self.trader_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                1,
                Decimal("140.00")
            )

            order_id = order.id

            success, message = accept_user_order(order_id)

            self.assertFalse(success)

    def test_accept_nonexistent_order(self):
        with self.logged_in(self.trader_id):
            success, message = accept_user_order(99999)

            self.assertFalse(success)

    def test_accept_buy_order_insufficient_shares(self):
        self.create_portfolio(self.seller_id, 1)

        with self.logged_in(self.buyer_id):
            _, _, order = create_user_order(
                "AAPL",
                "BUY",
                3,
                Decimal("140.00")
            )

            order_id = order.id

        with self.logged_in(self.seller_id):
            success, message = accept_user_order(order_id)

            self.assertFalse(success)

    def test_accept_sell_order_insufficient_funds(self):
        self.create_portfolio(self.seller_id, 10)

        with app.app_context():
            buyer = db.session.get(User, self.buyer_id)
            buyer.cash_balance = 100
            db.session.commit()

        with self.logged_in(self.seller_id):
            _, _, order = create_user_order(
                "AAPL",
                "SELL",
                3,
                Decimal("50000.00")
            )

            order_id = order.id

        with self.logged_in(self.buyer_id):
            success, message = accept_user_order(order_id)

            self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()