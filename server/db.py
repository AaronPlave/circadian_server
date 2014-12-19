import pymongo
import os
from bson.objectid import ObjectId
import json

MONGO_URI = os.environ.get('MONGOLAB_URI')
if not MONGO_URI:
    MONGO_URI = 'mongodb://localhost:27017/circadian'

client = pymongo.MongoClient(MONGO_URI)
db = client.get_default_database()
SOURCES = db["sources"]
USERS = db["users"]

def get_user(user_id):
    user = USERS.find({"user_id":user_id})
    if user.count() != 0:
        return user

def add_user(user_id):
    """
    Adds a user if the user does not already exist
    """
    if not get_user(user_id):
        print USERS.insert({"user_id":user_id,"sources":[]})
    else:
        print "User already exists, not adding."

def remove_user(user_id):
    if get_user(user_id):
        print USERS.remove({"user_id":user_id})
    else:
        print "Cannot remove user",user_id,"does not exist."

def add_source_to_user(source_id,user_id):
    user = get_user(user_id)
    if not user:
        print "No user, can't add source to user."
    sources = user[0]["sources"]
    sources.append(source_id)
    query = {"sources":sources}
    print USERS.update({'user_id':user_id},{"$set":query},upsert=False)


def remove_source_from_user(source_id,user_id):
    user = get_user(user_id)
    if not user:
        print "No user, can't remove source from user."
        return

    sources = user[0]["sources"]
    if source_id in sources:
        source_id.remove(source_id)
        query = {"sources":sources}
        print USERS.update({'user_id':user_id},{"$set":query},upsert=False)
    else:
        print "source_id not in user_id!"

def format_song(song):
    """
    Replaces the source_id mongo object with a 
    string version of the object. 
    """
    print song["source_id"]
    song["source_id"] = str(song["source_id"])
    return song

def get_user_songs(user_id):
    user = get_user(user_id)
    if not user:
        print "No user, can't get source from user."
        return "No such user: " + str(user_id)
    sources = user[0]["sources"]
    if not sources:
        print "No sources, nothing to return"
        return {}

    #otherwise, aggregate all songs over all the sources
    # print sources, "USER",user_id,"'s sources"
    songs = []
    for s in sources:
        source_obj =  SOURCES.find({"_id":s})[0]
        songs.append(source_obj["songs"])

    #flatten lists
    flatten = [format_song(song) for source in songs for song in source]

    #dump using bson/json to string
    dumped = json.dumps(flatten)
    return dumped


def get_source_by_url(source_url):
    """
    Returns the MongoObject with source_url == source_url if one exists.
    """
    # look up in db
    result = SOURCES.find({"source_url": source_url})
    if result.count() != 0:
        return result


def get_source_by_id(source_id):
    """
    Returns the MongoObject with id == source_id if one exists.
    """
    pass

def add_song_to_source(song_data,source_id):
    """
    Song is a dictionary returned from the scraper. Song is added if does
    not already exist in the db under the specified stream_url.
    """
    user = song_data.get("user")
    opt_fields = ["_id","title", "genre", "stream_url", "artwork_url", "created_at"]
    song = {k: song_data.get(k) for k in opt_fields}
    if user:
        username = user.get('username')
        if username:
            song["username"] = username

    # add the source_id to the song
    song["source_id"] = ObjectId(source_id)

    # Retrieve the source by source_id
    result = SOURCES.find({"_id": source_id})
    if result.count() == 0:
        print "SOURCE:",source_id,"not found, unable to add song:",song
        return False

    source_songs = result[0]["songs"]
    print source_songs,"SOURCE SONGS"
    for i in source_songs:
        if i["stream_url"] == song["stream_url"]:
            print "Song already exists in specified source, skipping."
            return

    source_songs.append(song)
    query = {"songs":source_songs}
    SOURCES.update({'_id':ObjectId(source_id)},{"$set":query},upsert=False)

def list_sources():
    """
    Returns a list of all the source urls in the db
    """
    return list(SOURCES.find())

def add_source_to_db(source_url, rss_url="", songs=[]):
    return SOURCES.insert({"source_url": source_url, "rss_url":rss_url, "songs": songs})

