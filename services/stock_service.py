from models.models import Stock


# =========================
# GET ALL STOCKS
# =========================
# Retrieves all stocks currently available in the game.
def get_all_stocks():
    return Stock.query.all()


# =========================
# GET ONE STOCK
# =========================
# Retrieves a stock using its ticker symbol.
def get_stock_by_ticker(ticker):
    return Stock.query.filter_by(ticker=ticker.upper()).first()
