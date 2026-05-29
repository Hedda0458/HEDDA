from flask import (
    Flask,
    redirect,
    url_for
)

from app.extensions import (
    db,
    login_manager
)

from app.core.config import Config

from app.models.user import User


def create_app():

    print("🚀 CREATE_APP EXECUTÉ")

    app = Flask(__name__)

    app.config.from_object(Config)

    # INIT EXTENSIONS
    db.init_app(app)

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):

        return db.session.get(
            User,
            int(user_id)
        )

    # IMPORT BLUEPRINTS
    from app.controllers.auth import bp as auth_bp

    from app.controllers.agents import bp as agents_bp

    # REGISTER
    app.register_blueprint(auth_bp)

    app.register_blueprint(agents_bp)

    # HOME
    @app.route("/")
    def home():

        return redirect(
            url_for("agents.list_agents")
        )

    # CREATE TABLES
    with app.app_context():

        db.create_all()

    return app