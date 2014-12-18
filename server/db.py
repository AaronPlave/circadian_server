import pymongo
import os

# Standard URI format: mongodb://[dbuser:dbpassword@]host:port/dbname
MONGODB_URI = 'mongodb://heroku_app32610402:e5qn8bjvu94bgmg6aqo8lfecd@ds027741.mongolab.com:27741/heroku_app32610402'

MONGO_URL = os.environ.get('MONGO_URL')
if not MONGO_URL:
    MONGODB_URI = "mongodb://localhost:27017/circadian"

client = pymongo.MongoClient(MONGODB_URI)
db = client.circadian
SOURCES = db["sources"]


def get_source_by_url(source_url):
    """
    Returns the MongoObject with source_url == source_url if one exists.
    """
    result = SOURCES.find({"source_url": source_url})
    if result.count() != 0:
        return "NO"


def get_source_by_id(source_id):
    """
    Returns the MongoObject with id == source_id if one exists.
    """
