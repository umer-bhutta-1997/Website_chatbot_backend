import unittest

from auth import db
from auth.models import User

from flask_testing import TestCase

from auth import app, db


class BaseTestCase(TestCase):
    """ Base Tests """

    def create_app(self):
        app.config.from_object('auth.config.DevelopmentConfig')
        return app

    def setUp(self):
        db.create_all()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class TestUserModel(BaseTestCase):

    # def test_encode_auth_token(self):
    #     user = User(
    #         email='test@test.com',
    #         password='test'
    #     )
    #     db.session.add(user)
    #     db.session.commit()
    #     auth_token = user.encode_auth_token(user.id)
    #     self.assertTrue(isinstance(auth_token, bytes))

    def test_decode_auth_token(self):
        user = User(
            email='test@test.com',
            password='test'
        )
        db.session.add(user)
        db.session.commit()
        auth_token = user.encode_auth_token(user.id)
        self.assertTrue(isinstance(auth_token, bytes))

        self.assertTrue(User.decode_auth_token(
            auth_token.decode("utf-8") ) == 1)


if __name__ == '__main__':
    unittest.main()