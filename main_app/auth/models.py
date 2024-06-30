import jwt
import datetime
from flask_migrate import upgrade
from auth import app, db, bcrypt


def create_table_if_not_exists():
    with app.app_context():
        # Use inspect to check if the table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table(User.__tablename__):
            # Create the table in the database if it doesn't exist
            db.create_all()
            print(f"Table '{User.__tablename__}' created successfully.")
        else:
            print(f"Table '{User.__tablename__}' already exists.")

       # upgrade(directory='machine_talk/migrations')
        print(f"Migrations for table '{User.__tablename__}' applied successfully.")


class User(db.Model):
    """ User Model for storing user related details """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    city = db.Column(db.String(100))   
    state = db.Column(db.String(100))  
    country = db.Column(db.String(100)) 
    last_login = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    def __init__(self, email, password, admin=False, city=None, state=None, country=None):
        self.email = email
        self.password = bcrypt.generate_password_hash(
            password, app.config.get('BCRYPT_LOG_ROUNDS')
        ).decode()
        self.registered_on = datetime.datetime.now()
        self.admin = admin
        self.city = city
        self.state = state
        self.country = country

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token
        :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=10, minutes=30, seconds=60),
                'iat': datetime.datetime.utcnow(),
                'sub': user_id
            }
            # print(payload)
            # print(jwt.encode(
            #     payload,
            #     app.config.get('SECRET_KEY'),
            #     algorithm='HS256'
            # ))
            return jwt.encode(
                payload,
                app.config.get('SECRET_KEY'),
                algorithm='HS256'
            )
            
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Validates the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'), algorithms='HS256')
            is_blacklisted_token = BlacklistToken.check_blacklist(auth_token)
            if is_blacklisted_token:
                return 'Token blacklisted. Please log in again.'
            else:
                return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'


class BlacklistToken(db.Model):
    """
    Token Model for storing JWT tokens
    """
    __tablename__ = 'blacklist_tokens'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return '<id: token: {}'.format(self.token)

    @staticmethod
    def check_blacklist(auth_token):
        # check whether auth token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(auth_token)).first()
        if res:
            return True
        else:
            return False
        

class ScrappedDates(db.Model):
    """
    Model for storing scrapped dates
    """
    __tablename__ = 'scrapped_dates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    page_name = db.Column(db.String(255), nullable=False)

    def __init__(self, date, page_name):
        self.date = date
        self.page_name = page_name


    def __repr__(self):
        return '<id: {}, date: {}, page_name: {}>'.format(self.id, self.date, self.page_name)
    

class conversationHistory(db.Model):
    """
    Model for storing the conversation hsitory data into database 
    """
    __tablename__ = 'conversation_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String, nullable=False)
    question = db.Column(db.String, nullable=False)
    response = db.Column(db.String, nullable=False)

    def __init__(self, user_id, question, response):
        self.user_id = user_id
        self.question = question
        self.response = response
