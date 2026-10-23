from flask import Flask
from config import Config
from .extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes import auth, main, beneficiaries, cases, reports, admin
    for module in (auth, main, beneficiaries, cases, reports, admin):
        app.register_blueprint(module.bp)

    from .cli import register_cli
    register_cli(app)

    return app
