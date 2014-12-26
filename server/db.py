import pymongo
import os
from bson.objectid import ObjectId

MONGO_URI = os.environ.get('MONGOLAB_URI')
if not MONGO_URI:
    MONGO_URI = 'mongodb://localhost:27017/circadian'

client = pymongo.MongoClient(MONGO_URI)
db = client.get_default_database()
SOURCES = db["sources"]
USERS = db["users"]
STATUS = db["status"]

def get_user(user_id):
    user = USERS.find({"user_id":user_id})
    if user.count() != 0:
        return user

def add_user(user_id):
    """
    Adds a user if the user does not already exist.
    """
    if not get_user(user_id):
        if USERS.insert({"user_id":user_id,"sources":[]}):
            return True
    else:
        print "DB: User already exists, not adding."

def remove_user(user_id):
    if get_user(user_id):
        if USERS.remove({"user_id":user_id}):
            return True
    else:
        print "DB: Cannot remove user",user_id,"does not exist."

def link_source_and_user(sourceID,user_id):
    # add source to user
    print "LINKIING!"
    user = get_user(user_id)
    if not user:
        print "DB: No user, can't add source:",sourceID,"to user:",user_id
        return
    user_sources = user[0]["sources"]
    if sourceID not in user_sources:
        user_sources.append(sourceID)
        query = {"sources":user_sources}
        if not USERS.update({'user_id':user_id},{"$set":query},upsert=False):
            print "DB: failed to add source:",sourceID,"to user:",user_id
            return False
    else:
        print "DB: User:",user_id,"already has source",sourceID,",not adding source to user."

    # add user to sources
    source = get_source_by_id(sourceID)
    if not source:
        print "DB: No source, can't add user:",user_id,"to source:",sourceID
        return

    source_users = source[0]["users"]
    if user_id not in source_users:
        user_sources.append(sourceID)
        query2 = {"users":user_sources}
        print query2
        if not SOURCES.update({'_id':sourceID},{"$set":query2},upsert=False):
            print "DB: failed to add user:",user_id,"to source:",sourceID
            return False
    else:
        print "DB: Source:",sourceID,"already has user",user_id,",not adding user to source."
    print SOURCES.find_one()
    print USERS.find_one()
    return True

    

def remove_source_from_user(sourceID,user_id):
    user = get_user(user_id)
    if not user:
        print "DB: No user, can't remove source:",sourceID,"from user:",user_id
        return

    sources = user[0]["sources"]
    if sourceID in sources:
        sourceID.remove(sourceID)
        query = {"sources":sources}
        if USERS.update({'user_id':user_id},{"$set":query},upsert=False):
            return True
        else:
            print "DB: Could not remove source:",sourceID,"from user:",user_id
    else:
        print "DB: sourceID:",sourceID,"not in user_id:",user_id

def remove_all_sources():
    SOURCES.drop()
    if SOURCES.count() == 0:
        return True
    else:
        print "Unable to remove all sources"


def format_id(song):
    """
    Replaces the sourceID mongo object with a 
    string version of the object. 
    """
    song["sourceID"] = str(song["sourceID"])
    return song

def format_ids(songs):
    return [format_id(s) for s in songs]

def get_user_songs(user_id):
    user = get_user(user_id)
    if not user:
        print "DB: No user, can't get source from user."
        return "DB: No such user:",user_id
    sources = user[0]["sources"]
    if not sources:
        print "DB: No sources for user:",user_id,"no songs to return."
        return {}

    #otherwise, aggregate all songs over all the sources
    # print sources, "USER",user_id,"'s sources"
    songs = []
    for s in sources:
        source_obj =  SOURCES.find({"_id":s})[0]
        songs.append(source_obj["songs"])

    #flatten lists
    flatten = [format_id(song) for source in songs for song in source]

    return flatten


def get_source_by_url(source_url):
    """
    Returns the MongoObject with source_url == source_url if one exists.
    """
    # look up in db
    result = SOURCES.find({"source_url": source_url})
    if result.count() != 0:
        return result


def get_source_by_id(sourceID):
    """
    Returns the MongoObject with id == sourceID if one exists.
    """
    result = SOURCES.find({"_id": sourceID})
    if result.count() != 0:
        return result

def add_song_to_source(song_data,sourceID):
    """
    Song is a dictionary returned from the scraper. Song is added if does
    not already exist in the db under the specified streamURL.
    """
    opt_fields = ["_id","title", "genre", "streamURL", "artworkURL", "date","artist"]
    song = {k: song_data.get(k) for k in opt_fields}

    # add the sourceID to the song
    song["sourceID"] = ObjectId(sourceID)

    # retrieve the source by sourceID
    result = SOURCES.find({"_id": sourceID})
    if result.count() == 0:
        print "DB: ",sourceID,"not found, unable to add song:",song
        return

    # change the artwork url to larger size
    aurl = song.get("artworkURL")
    if aurl:
        song["artworkURL"] = aurl.replace("-large","-t500x500")

    source_songs = result[0]["songs"]
    for i in source_songs:
        if i["streamURL"] == song["streamURL"]:
            print "DB: Song already exists in specified source, skipping."
            return

    source_songs.append(song)
    query = {"songs":source_songs}
    if SOURCES.update({'_id':ObjectId(sourceID)},{"$set":query},upsert=False):
        return True
    else:
        print "DB: Unable to add song:",song_data.get("_id"),"to source:",sourceID

def list_sources():
    """
    Returns a list of all the source urls in the db
    """
    return list(SOURCES.find())

def add_source_to_db(source_url, rss_url="", songs=[]):
    source = SOURCES.insert({"source_url": source_url, "rss_url":rss_url, "songs": songs, "users":[]})
    if source:
        return source
    else:
        print "Unable to add source url:",source_url,"to db"


def get_last_update_time():
    last_update = STATUS.find_one()
    if last_update:
        return last_update["update_time"].ctime()
    return {"update_time":"never"}

def set_last_update_time(update_time):
    obj = STATUS.find_one()
    if not obj:
        if STATUS.insert({"update_time":update_time,}):
            return True
    query = {"update_time":update_time}
    if STATUS.update({'_id':obj["_id"]},{"$set":query},upsert=False):
        return True

def remove_all():
    USERS.drop()
    STATUS.drop()
    SOURCES.drop()
