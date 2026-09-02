import os
from flask import Flask
from models.models import db
from controllers.auth_controller import auth_controller
from controllers.stock_controller import stock_controller
from controllers.frontend_controller import frontend_controller

app = Flask(__name__)

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


@app.route("/")
def home():
    return "<h1>Stock Trading Simulator</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
