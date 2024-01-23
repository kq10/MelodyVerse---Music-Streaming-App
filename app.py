from flask import Flask 
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash

from config import Config
from db import db

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
from models import *
bcrypt= Bcrypt(app)
app.app_context().push()
db.create_all()

def create_admin():
    admin=User.query.filter_by(email='admin@melodyverse.com').first()
    if admin is None:
        admin = User(
            username='admin',
            email='admin@melodyverse.com',
            password=generate_password_hash('admin')
        )
        admin.is_admin=True
        db.session.add(admin)
        db.session.commit()

    else:
        print('Admin account already exists')


if __name__=='__main__':
    from controllers.routes import *
    create_admin()
    app.run(debug=True,port=8080)
