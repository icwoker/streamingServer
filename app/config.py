import datetime
class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:123456@localhost:5432/test'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '12345'
    JWT_SECRET_KEY = 'istreaming'
    JWT_EXPIRATION_DELTA = datetime.timedelta(days=1)