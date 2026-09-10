import os
import threading
from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from models.models import db
from controllers.auth_controller import auth_controller
from controllers.stock_controller import stock_controller
from controllers.frontend_controller import frontend_controller
from controllers.admin_controller import admin_bp
from controllers.order_controller import order_controller
from controllers.portfolio_controller import portfolio_controller
from services.game_service import run_game_timer
from controllers.game_controller import game_controller
from prometheus_flask_exporter import PrometheusMetrics


app = Flask(__name__)

metrics = PrometheusMetrics(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}/"
    f"{os.getenv('DB_NAME')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.register_blueprint(auth_controller)
app.register_blueprint(stock_controller)
app.register_blueprint(frontend_controller)
app.register_blueprint(admin_bp)
app.register_blueprint(order_controller)
app.register_blueprint(portfolio_controller)
app.register_blueprint(game_controller)


@app.route("/")
def home():
    return "<h1>Stock Trading Simulator</h1>"


if __name__ == "__main__":

    timer_thread = threading.Thread(
        target=run_game_timer,
        args=(app,),
        daemon=True
    )

    timer_thread.start()

    app.run(host="0.0.0.0", port=5000)
