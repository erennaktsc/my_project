from flask import Flask
from flask_login import LoginManager
from app.models import db, User
import os
import json as json_lib

login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmalısın.'
login_manager.login_message_category = 'error'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    app = Flask(__name__)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eduscan.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['SECRET_KEY'] = 'eduscan-secret-key-degistirilmeli-uretimde'
    
    db.init_app(app)
    login_manager.init_app(app)
    
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        if not value:
            return []
        try:
            return json_lib.loads(value)
        except:
            return []
    
    from app.routes import main
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
    
    return app