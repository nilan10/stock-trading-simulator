from flask import session

from models.models import (
    db,
    User,
    Stock,
    Portfolio,
    Order
)

from services.audit_service import log_audit_action


# ============================================================
# CREATE USER ORDER
# ============================================================

def create_user_order(
    ticker,
    order_type,
    quantity,
    price
):

    user_id = session.get("user_id")

    if not user_id:
        return False, "You must be logged in.", None

    user = db.session.get(
        User,
        user_id
    )

    if not user:
        return False, "User not found.", None

    if order_type not in [
        "BUY",
        "SELL"
    ]:
        return (
            False,
            "Order type must be BUY or SELL.",
            None
        )

    if (
        not isinstance(quantity, int)
        or quantity <= 0
    ):
        return (
            False,
            "Quantity must be a positive whole number.",
            None
        )

    if price is None or price <= 0:
        return (
            False,
            "Price must be greater than zero.",
            None
        )

    stock = Stock.query.filter_by(
        ticker=ticker.upper()
    ).first()

    if not stock:
        return False, "Stock not found.", None


    # ========================================================
    # SELL ORDER CHECK
    # ========================================================

    if order_type == "SELL":

        portfolio = Portfolio.query.filter_by(
            user_id=user.id,
            stock_id=stock.id
        ).first()

        if not portfolio:
            return (
                False,
                "You do not own any shares of this stock.",
                None
            )

        available_quantity = (
            portfolio.quantity
            - portfolio.reserved_quantity
        )

        if available_quantity < quantity:
            return (
                False,
                "You do not have enough unreserved shares.",
                None
            )


    # ========================================================
    # BUY ORDER CHECK
    # ========================================================

    if order_type == "BUY":

        total_cost = (
            price
            * quantity
        )

        available_cash = (
            user.cash_balance
            - user.reserved_cash
        )

        if available_cash < total_cost:
            return (
                False,
                "Insufficient available funds.",
                None
            )


    # ========================================================
    # CREATE ORDER
    # ========================================================

    order = Order(
        user_id=user.id,
        stock_id=stock.id,
        order_type=order_type,
        quantity=quantity,
        price=price,
        status="OPEN"
    )

    db.session.add(order)


    # Reserve shares or cash.

    if order_type == "SELL":

        portfolio.reserved_quantity += (
            quantity
        )

    else:

        user.reserved_cash += (
            total_cost
        )


    db.session.commit()


    log_audit_action(
        user.id,
        "ORDER_CREATED",
        f"{order_type} order #{order.id}: "
        f"{quantity} shares of "
        f"{stock.ticker} at "
        f"${price:.2f} per share."
    )


    return (
        True,
        "Order created successfully.",
        order
    )


# ============================================================
# GET OPEN PLAYER ORDERS
# ============================================================

def get_open_orders():

    orders = Order.query.filter(
        Order.status == "OPEN",
        Order.order_source == "PLAYER"
    ).order_by(
        Order.created_at.desc()
    ).all()


    open_orders = []


    for order in orders:

        stock = db.session.get(
            Stock,
            order.stock_id
        )

        user = db.session.get(
            User,
            order.user_id
        )


        open_orders.append({

            "order_id":
                order.id,

            # IMPORTANT:
            # Market page uses this to determine
            # whether this order belongs to the
            # currently logged-in user.
            "user_id":
                order.user_id,

            "username":
                user.username
                if user
                else "Unknown",

            "ticker":
                stock.ticker
                if stock
                else "N/A",

            "order_type":
                order.order_type,

            "quantity":
                order.quantity,

            "price":
                float(order.price),

            "status":
                order.status,

            "created_at":
                order.created_at.isoformat()
                if order.created_at
                else None

        })


    return open_orders


# ============================================================
# UPDATE USER ORDER
# ============================================================

def update_user_order(
    order_id,
    quantity,
    price
):

    user_id = session.get("user_id")


    if not user_id:
        return (
            False,
            "You must be logged in."
        )


    user = db.session.get(
        User,
        user_id
    )


    if not user:
        return (
            False,
            "User not found."
        )


    order = db.session.get(
        Order,
        order_id
    )


    if not order:
        return (
            False,
            "Order not found."
        )


    # Only the creator can edit it.

    if order.user_id != user.id:

        return (
            False,
            "You can only modify your own orders."
        )


    if order.status != "OPEN":

        return (
            False,
            "Only open orders can be modified."
        )


    if order.order_source != "PLAYER":

        return (
            False,
            "Market orders cannot be modified."
        )


    if (
        not isinstance(quantity, int)
        or quantity <= 0
    ):

        return (
            False,
            "Quantity must be a positive whole number."
        )


    if price is None or price <= 0:

        return (
            False,
            "Price must be greater than zero."
        )


    stock = db.session.get(
        Stock,
        order.stock_id
    )


    if not stock:

        return (
            False,
            "Stock not found."
        )


    # ========================================================
    # UPDATE SELL ORDER
    # ========================================================

    if order.order_type == "SELL":

        portfolio = Portfolio.query.filter_by(
            user_id=user.id,
            stock_id=stock.id
        ).first()


        if not portfolio:

            return (
                False,
                "Portfolio entry not found."
            )


        # Release the old reservation first.

        portfolio.reserved_quantity -= (
            order.quantity
        )


        if portfolio.reserved_quantity < 0:

            portfolio.reserved_quantity = 0


        available_quantity = (
            portfolio.quantity
            - portfolio.reserved_quantity
        )


        if available_quantity < quantity:

            db.session.rollback()

            return (
                False,
                "You do not have enough "
                "unreserved shares."
            )


        # Reserve the new amount.

        portfolio.reserved_quantity += (
            quantity
        )


    # ========================================================
    # UPDATE BUY ORDER
    # ========================================================

    else:

        old_reserved = (
            order.quantity
            * order.price
        )

        new_total_cost = (
            quantity
            * price
        )


        # Release old reserved cash.

        user.reserved_cash -= (
            old_reserved
        )


        if user.reserved_cash < 0:

            user.reserved_cash = 0


        available_cash = (
            user.cash_balance
            - user.reserved_cash
        )


        if available_cash < new_total_cost:

            db.session.rollback()

            return (
                False,
                "Insufficient available funds."
            )


        # Reserve new amount.

        user.reserved_cash += (
            new_total_cost
        )


    order.quantity = quantity
    order.price = price


    db.session.commit()


    log_audit_action(
        user.id,
        "ORDER_UPDATED",
        f"Updated order #{order.id}: "
        f"{order.order_type} "
        f"{quantity} shares of "
        f"{stock.ticker} "
        f"at ${price:.2f} per share."
    )


    return (
        True,
        "Order updated successfully."
    )


# ============================================================
# CANCEL USER ORDER
# ============================================================

def cancel_user_order(
    order_id
):

    user_id = session.get("user_id")


    if not user_id:

        return (
            False,
            "You must be logged in."
        )


    user = db.session.get(
        User,
        user_id
    )


    if not user:

        return (
            False,
            "User not found."
        )


    order = db.session.get(
        Order,
        order_id
    )


    if not order:

        return (
            False,
            "Order not found."
        )


    # Users can only cancel their own order.

    if order.user_id != user.id:

        return (
            False,
            "You can only cancel your own orders."
        )


    if order.status != "OPEN":

        return (
            False,
            "Only open orders can be cancelled."
        )


    if order.order_source != "PLAYER":

        return (
            False,
            "Market orders must be cancelled "
            "through the market order system."
        )


    stock = db.session.get(
        Stock,
        order.stock_id
    )


    # ========================================================
    # RELEASE RESERVED SHARES
    # ========================================================

    if order.order_type == "SELL":

        portfolio = Portfolio.query.filter_by(
            user_id=user.id,
            stock_id=order.stock_id
        ).first()


        if portfolio:

            portfolio.reserved_quantity -= (
                order.quantity
            )


            if portfolio.reserved_quantity < 0:

                portfolio.reserved_quantity = 0


    # ========================================================
    # RELEASE RESERVED CASH
    # ========================================================

    else:

        user.reserved_cash -= (
            order.quantity
            * order.price
        )


        if user.reserved_cash < 0:

            user.reserved_cash = 0


    # We do NOT remove the database row.
    # We keep it for history/auditing.

    order.status = "CANCELLED"


    db.session.commit()


    log_audit_action(
        user.id,
        "ORDER_CANCELLED",
        f"Cancelled order #{order.id} for "
        f"{order.quantity} shares of "
        f"{stock.ticker if stock else 'N/A'}."
    )


    return (
        True,
        "Order cancelled successfully."
    )


# ============================================================
# ACCEPT ANOTHER PLAYER'S ORDER
# ============================================================

def accept_user_order(
    order_id
):

    accepting_user_id = session.get(
        "user_id"
    )


    if not accepting_user_id:

        return (
            False,
            "You must be logged in."
        )


    accepting_user = db.session.get(
        User,
        accepting_user_id
    )


    if not accepting_user:

        return (
            False,
            "User not found."
        )


    order = db.session.get(
        Order,
        order_id
    )


    if not order:

        return (
            False,
            "Order not found."
        )


    if order.status != "OPEN":

        return (
            False,
            "This order is no longer available."
        )


    if order.order_source != "PLAYER":

        return (
            False,
            "Market orders cannot be "
            "accepted by other players."
        )


    # Cannot accept your own order.

    if order.user_id == accepting_user.id:

        return (
            False,
            "You cannot accept your own order."
        )


    stock = db.session.get(
        Stock,
        order.stock_id
    )


    if not stock:

        return (
            False,
            "Stock not found."
        )


    order_creator = db.session.get(
        User,
        order.user_id
    )


    if not order_creator:

        return (
            False,
            "Order creator not found."
        )


    total_value = (
        order.quantity
        * order.price
    )


    try:

        # ====================================================
        # SELL ORDER
        # ====================================================
        #
        # Creator = SELLER
        # Acceptor = BUYER
        #

        if order.order_type == "SELL":

            seller = order_creator
            buyer = accepting_user


            seller_portfolio = (
                Portfolio.query
                .filter_by(
                    user_id=seller.id,
                    stock_id=stock.id
                )
                .first()
            )


            if not seller_portfolio:

                return (
                    False,
                    "Seller does not own this stock."
                )


            if (
                seller_portfolio.reserved_quantity
                < order.quantity
            ):

                return (
                    False,
                    "Seller's reserved shares are invalid."
                )


            available_buyer_cash = (
                buyer.cash_balance
                - buyer.reserved_cash
            )


            if available_buyer_cash < total_value:

                return (
                    False,
                    "Insufficient funds."
                )


            buyer_portfolio = (
                Portfolio.query
                .filter_by(
                    user_id=buyer.id,
                    stock_id=stock.id
                )
                .first()
            )


            if not buyer_portfolio:

                buyer_portfolio = Portfolio(
                    user_id=buyer.id,
                    stock_id=stock.id,
                    quantity=0,
                    reserved_quantity=0,
                    avg_buy_price=0.00
                )

                db.session.add(
                    buyer_portfolio
                )


            # Transfer cash.

            buyer.cash_balance -= (
                total_value
            )

            seller.cash_balance += (
                total_value
            )


            # Consume seller's reserved shares.

            seller_portfolio.reserved_quantity -= (
                order.quantity
            )


            # Transfer shares.

            seller_portfolio.quantity -= (
                order.quantity
            )


            buyer_old_quantity = (
                buyer_portfolio.quantity
            )


            # Calculate buyer's new average cost.

            buyer_old_value = (
                float(
                    buyer_portfolio.avg_buy_price
                )
                * buyer_old_quantity
            )


            buyer_portfolio.quantity += (
                order.quantity
            )


            buyer_portfolio.avg_buy_price = (
                buyer_old_value
                + float(total_value)
            ) / buyer_portfolio.quantity


        # ====================================================
        # BUY ORDER
        # ====================================================
        #
        # Creator = BUYER
        # Acceptor = SELLER
        #

        else:

            buyer = order_creator
            seller = accepting_user


            seller_portfolio = (
                Portfolio.query
                .filter_by(
                    user_id=seller.id,
                    stock_id=stock.id
                )
                .first()
            )


            if not seller_portfolio:

                return (
                    False,
                    "Seller does not own this stock."
                )


            available_seller_quantity = (
                seller_portfolio.quantity
                - seller_portfolio.reserved_quantity
            )


            if (
                available_seller_quantity
                < order.quantity
            ):

                return (
                    False,
                    "Seller does not have enough "
                    "unreserved shares."
                )


            # BUY order creator already reserved money.

            if buyer.reserved_cash < total_value:

                return (
                    False,
                    "Buy order reservation is invalid."
                )


            buyer_portfolio = (
                Portfolio.query
                .filter_by(
                    user_id=buyer.id,
                    stock_id=stock.id
                )
                .first()
            )


            if not buyer_portfolio:

                buyer_portfolio = Portfolio(
                    user_id=buyer.id,
                    stock_id=stock.id,
                    quantity=0,
                    reserved_quantity=0,
                    avg_buy_price=0.00
                )

                db.session.add(
                    buyer_portfolio
                )


            # =================================================
            # TRANSFER MONEY
            # =================================================

            buyer.reserved_cash -= (
                total_value
            )

            buyer.cash_balance -= (
                total_value
            )

            seller.cash_balance += (
                total_value
            )


            # =================================================
            # TRANSFER SHARES
            # =================================================

            seller_portfolio.quantity -= (
                order.quantity
            )


            buyer_old_quantity = (
                buyer_portfolio.quantity
            )


            buyer_old_value = (
                float(
                    buyer_portfolio.avg_buy_price
                )
                * buyer_old_quantity
            )


            buyer_portfolio.quantity += (
                order.quantity
            )


            buyer_portfolio.avg_buy_price = (
                buyer_old_value
                + float(total_value)
            ) / buyer_portfolio.quantity


            # Remove empty seller portfolio.

            if seller_portfolio.quantity == 0:

                db.session.delete(
                    seller_portfolio
                )


        # ====================================================
        # COMPLETE ORDER
        # ====================================================

        order.status = "EXECUTED"

        order.accepted_by_user_id = (
            accepting_user.id
        )

        order.accepted_at = (
            db.func.current_timestamp()
        )

        order.executed_at = (
            db.func.current_timestamp()
        )


        db.session.commit()


    except Exception as e:

        db.session.rollback()

        return (
            False,
            f"Trade failed: {str(e)}"
        )


    log_audit_action(
        accepting_user.id,
        "ORDER_ACCEPTED",
        f"Accepted order #{order.id} for "
        f"{order.quantity} shares of "
        f"{stock.ticker}."
    )


    return (
        True,
        "Trade executed successfully."
    )