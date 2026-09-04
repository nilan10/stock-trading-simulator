from flask import Blueprint, render_template, session, jsonify

from models.models import (
    db,
    User,
    Portfolio,
    Stock
)


frontend_controller = Blueprint(
    "frontend",
    __name__
)


# =========================
# FRONTEND HOME
# =========================

@frontend_controller.route("/app")
def frontend():

    return render_template(
        "index.html"
    )


# =========================
# MARKET PAGE
# =========================

@frontend_controller.route("/market")
def market():

    return render_template(
        "market.html"
    )


# =========================
# REGISTER PAGE
# =========================

@frontend_controller.route("/register-page")
def register_page():

    return render_template(
        "register.html"
    )


# =========================
# CURRENT USER
# =========================

@frontend_controller.route("/me")
def me():

    return jsonify({

        "user_id":
            session.get("user_id"),

        "username":
            session.get("username"),

        "role":
            session.get("role")

    })


# =========================
# ADMIN PAGE
# =========================

@frontend_controller.route("/admin-page")
def admin_page():

    return render_template(
        "admin.html"
    )


# =========================
# PLAYER LEADERBOARD
# =========================

@frontend_controller.route(
    "/leaderboard",
    methods=["GET"]
)
def leaderboard():

    # User must be logged in.
    if not session.get("user_id"):

        return jsonify({
            "error":
                "You must be logged in."
        }), 401


    # Only actual Trader accounts are
    # included in the rankings.
    traders = (
        User.query
        .filter_by(role="Trader")
        .order_by(User.id)
        .all()
    )


    leaderboard_data = []


    for user in traders:

        # Find every stock this user owns.
        holdings = (
            Portfolio.query
            .filter_by(
                user_id=user.id
            )
            .all()
        )


        holdings_value = 0.0


        # Calculate the CURRENT value
        # of all stocks owned.
        for holding in holdings:

            stock = db.session.get(
                Stock,
                holding.stock_id
            )


            if not stock:
                continue


            holdings_value += (
                float(holding.quantity)
                *
                float(stock.current_price)
            )


        # Get the player's current cash.
        cash_balance = float(
            user.cash_balance or 0
        )


        # Total account value =
        # cash + current stock value.
        total_portfolio_value = (
            cash_balance
            +
            holdings_value
        )


        leaderboard_data.append({

            "user_id":
                user.id,

            "username":
                user.username,

            "cash_balance":
                cash_balance,

            "holdings_value":
                holdings_value,

            "total_portfolio_value":
                total_portfolio_value

        })


    # Highest portfolio value goes first.
    leaderboard_data.sort(

        key=lambda player: (
            -player[
                "total_portfolio_value"
            ],
            player[
                "username"
            ].lower()
        )

    )


    # Give everyone a rank:
    # 1, 2, 3, 4...
    for index, player in enumerate(
        leaderboard_data,
        start=1
    ):

        player["rank"] = index


    return jsonify(
        leaderboard_data
    ), 200