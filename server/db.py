import pymongo
import os
import datetime
from bson.objectid import ObjectId
from scraping import TIME_DELTA, uuid


MONGO_URI = os.environ.get('MONGOLAB_URI')
if not MONGO_URI:
    MONGO_URI = 'mongodb://localhost:27017/circadian'

client = pymongo.MongoClient(MONGO_URI)
db = client.get_default_database()
SOURCES = db["sources"]
USERS = db["users"]
STATUS = db["status"]
GROUPS = db["groups"]

def get_user(user_id):
    user = USERS.find({"user_id":user_id})
    if user.count() != 0:
        return user

def get_user_by_mongo_id(mongo_id):
    user = USERS.find({"_id":ObjectId(mongo_id)})
    if user.count() !=0:
        return user

def get_groups_by_user_id(user_id):
    user = get_user(user_id)
    if not user:
        print "DB: Could not get user in get_group_by_user_id"
        return []
    user = user[0]
    user_groups = user["groups"]
    final_groups = []
    for groupID in user_groups:
        group = GROUPS.find({"_id":groupID})
        if group.count() == 0:
            print "DB: Unable to find group:",groupID
            continue
        group = group[0]
        # get all the users
        if group["users"]:
            group_users = list(USERS.find({"user_id":{"$in":group["users"]}}))
            for i in group_users:
                del i["_id"]
                del i["groups"]
                del i["recommendations"]
                del i["sources"]
                del i["deviceTokens"]
                i["userID"] = i["user_id"]
                del i["user_id"]

            group["users"] = group_users
        # generate a new unique id for the song
        group["_id"] = str(uuid.uuid4())[0:8]
        final_groups.append(group)
    return final_groups

def add_song_to_group(songID,sourceID,groupID,user_id):
    """
    Adds the song object with _id == songID found in the source w/_id == sourceID 
    to the group with _id == groupID.
    """
    # get group
    group = GROUPS.find({"_id":ObjectId(groupID)})
    if group.count() == 0:
        print "DB: Unable to find group:",groupID
        return
    group = group[0]

    # get the source
    source = get_source_by_id(ObjectId(sourceID))
    if not source:
        print "DB: Unable to find source for add_song_to_group"
        return
    source = source[0]

    # find song in source
    song_match = None
    for i in source["songs"]:
        if i["_id"] == songID:
            song_match = i
            break
    if not song_match:
        print "DB: Unable to find songID:",songID,"in source",sourceID,"can't add to group:",groupID
        return
    song_match["sourceID"] = str(song_match["sourceID"])
    song_match["userID"] = str(user_id)
    song_match["postDate"] = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    group["songs"].append(song_match)
    
    # add song to group
    query = {"songs":group["songs"]}
    res = GROUPS.update({'_id':ObjectId(groupID)},{"$set":query},upsert=False)
    if res:
        return True

def add_group(name,users):
    # add the group ID to each user (each user is a user_id)
    user_objs = []
    for i in users:
        u = get_user(i)
        if u:
            user_objs.append(u[0])
        else:
            print "DB: Could not get user in add_group, not adding to group:",name
    
    # if no valid users, why add the group
    if len(user_objs) == 0:
        print "DB: add_group no valid users, not adding group"
        return False

    valid_user_ids = [i["user_id"] for i in user_objs]
    groupID = GROUPS.insert({"name":name,"users":valid_user_ids,"songs":[]})
    if not groupID:
        print "DB: No group ID in add_group"
        return False

    for u in user_objs:
        groups = u["groups"]
        if groupID not in groups:
            groups.append(groupID)
            query = {"groups":groups}
            res = USERS.update({'user_id':u["user_id"]},{"$set":query},upsert=False)
            if not res:
                print "DB: Could not add group to user:",u["_id"]
    return True

def add_user_to_group(user_id,group_id):
    """
    Adds user to group and group to user.
    """
    # get user
    user = get_user(user_id)
    if not user:
        print "DB: Could not get user in add_user_to_group"
        return
    user = user[0]
    user_mongo_id = user["_id"]

    # add user to group
    group = GROUPS.find({"_id":group_id})
    if group.count() == 0:
        print "DB: Unable to find group:",group_id
        return False
    group = group[0]
    group_users = group["users"]
    if user_mongo_id not in group_users:
        group_users.append(user_mongo_id)
        query = {"users":group_users}
        res = GROUPS.update({'_id':group_id},{"$set":query},upsert=False)
        if not res:
            print "DB: Could not add user:",user_id,"to group:",group_id
            return False
    
    # add group to user
    user_groups = user["groups"]
    if group_id not in user_groups:
        user_groups.append(group_id)
        query = {"groups":user_groups}
        res = USERS.update({'_id':user_mongo_id},{"$set":query},upsert=False)
        if not res:
            print "DB: Could not add group:",group_id,"to user:",user_id
            return False
    return True

def remove_group(group_id):
    if GROUPS.remove({"_id":group_id}):
        return True
    return False

def remove_user_from_group(user_id,group_id):
    # get user
    user = get_user(user_id)
    if not user:
        print "DB: Couldn't get user in remove user from group"
        return False
    user_mongo_id = user[0]["_id"]

    # remove the group from the user
    group = GROUPS.find({'_id':group_id})
    if group.count() == 0:
        print "DB: unable to remove user:",user_id,"from group:",group_id
        return False
    users = group[0]["users"]
    if user_mongo_id in users:
        print users,"u1"
        users.remove(user_mongo_id)

        #if the group has no more users, delete it
        if len(users) == 0:
            remove_group(group_id)
        else:
            print users,"u2"
            query = {"users":users}
            if not GROUPS.update({'_id':group_id},{"$set":query},upsert=False):
                print "DB: Could not remove user:",user_id,"from group:",group_id
                return False

        # remove the group from the user
        user_groups = user[0]["groups"]
        if group_id in user_groups:
            user_groups.remove(group_id)
            query = {"groups":user_groups}
            res = USERS.update({'_id':user_mongo_id},{"$set":query},upsert=False)
            if not res:
                print "DB: Could not remove group:",group_id,"from user:",user_id
                return False
    return True

def update_user_recommendations(user_id,new_recs):
    user = get_user(user_id)
    if not user:
        print "DB: No user, can't get user:",user_id,"recommendations."
        return []
    query = {"recommendations":new_recs}
    return USERS.update({'user_id':user_id},{"$set":query},upsert=False)

def get_user_recommendations(user_id):
    user = get_user(user_id)
    if not user:
        print "DB: No user, can't get user:",user_id,"recommendations."
        return []
    user_recs = user[0]["recommendations"]
    #turn source object ids into full sources!
    full_recs = []
    for i in user_recs:
        source = get_source_by_id(i)
        if not source:
            continue
        full_recs.append(source[0])
    return full_recs

def add_user(user_id,profilePictureURL,name,deviceToken):
    """
    Adds a user if the user does not already exist.
    """
    u = get_user(user_id)
    if not u:
        if USERS.insert({"user_id":user_id,"sources":[],"recommendations":[],
            "groups":[],"profilePictureURL":profilePictureURL,
            "name":name,"deviceTokens":[deviceToken]}):
            return True
        else:
            print "DB: Unable to insert new user."
            return False
    else:
        # print "DB: User already exists, checking for updates."
        query = {}
        # print "DB:",deviceToken,profilePictureURL,name,u[0]
        if deviceToken not in u[0]["deviceTokens"]:
            query["deviceToken"].append(deviceToken)
        if u[0]["profilePictureURL"] != profilePictureURL:
            query["profilePictureURL"] = profilePictureURL
        if u[0]["name"] != name:
            query["name"] = name
        # print "DB: QUERY:",query
        if query:
            # print "DB: Updating user:",user_id,name
            if USERS.update({'user_id':user_id},{"$set":query},upsert=False):
                return True
            else:
                print "DB: Unable to update old user."
                return False
        else:
            print "DB: Nothing to update for user:",user_id,name


def remove_user(user_id):
    if get_user(user_id):
        if USERS.remove({"user_id":user_id}):
            return True
    else:
        print "DB: Cannot remove user",user_id,"does not exist."

def link_source_and_user(sourceID,user_id):
    # add source to user
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
    # else:
    #     print "DB: User:",user_id,"already has source",sourceID,",not adding source to user."

    # add user to sources
    source = get_source_by_id(sourceID)
    if not source:
        print "DB: No source, can't add user:",user_id,"to source:",sourceID
        return
    source_users = source[0]["users"]
    if user_id not in source_users:
        source_users.append(user_id)
        query2 = {"users":source_users}
        if not SOURCES.update({'_id':sourceID},{"$set":query2},upsert=False):
            print "DB: failed to add user:",user_id,"to source:",sourceID
            return False
    # else:
    #     print "DB: Source:",sourceID,"already has user",user_id,",not adding user to source."
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

def remove_old_songs():
    current_time = datetime.datetime.now()
    for i in SOURCES.find():
        source_songs = i["songs"]
        songs_to_rmv = []
        for j in source_songs:
            j_date = j["date"]
            j_date = j_date.split()
            j_date = " ".join(j_date[0:len(j_date)-1])
            j_date = datetime.datetime.strptime(j_date, '%Y/%m/%d %H:%M:%S')
            delta = current_time - j_date
            hours = (delta.days*24)+(delta.seconds/60.0/60.0)
            if hours > TIME_DELTA:
                songs_to_rmv.append(j)

        # if no old songs, done!
        if len(songs_to_rmv) == 0:
            continue

        for j in songs_to_rmv:
            source_songs.remove(j)
        query = {"songs":source_songs}
        if not SOURCES.update({'_id':i["_id"]},{"$set":query},upsert=False):
            print "DB: Unable to remove old songs, update failed in source:", i["sourceID"]

    return True

def remove_old_group_songs():
    for i in GROUPS.find():
        group_songs = i["songs"]
        songs_to_rmv = []
        for j in group_songs:
            post_date = datetime.datetime.strptime(j["postDate"],"%Y-%m-%d %H:%M:%S")
            j_date = j["date"]
            j_date = j_date.split()
            j_date = " ".join(j_date[0:len(j_date)-1])
            j_date = datetime.datetime.strptime(j_date, '%Y/%m/%d %H:%M:%S')
            delta = post_date - j_date
            hours = (delta.days*24)+(delta.seconds/60.0/60.0)
            if hours > TIME_DELTA:
                songs_to_rmv.append(j)

        # if no old group songs, done!
        if len(songs_to_rmv) == 0:
            continue

        for j in songs_to_rmv:
            group_songs.remove(j)
        query = {"songs":group_songs}
        if not GROUPS.update({'_id':i["_id"]},{"$set":query},upsert=False):
            print "DB: Unable to remove old group songs, update failed in source:", i["sourceID"]

    return True

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
        return []
    sources = user[0]["sources"]
    if not sources:
        print "DB: No sources for user:",user_id,"no songs to return."
        return []

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

# def get_sc_source_by_mongo_id(sc_id):

def get_sc_source_by_sc_id(sc_id):
    """
    Return the MongoObject with sc_id == sc_id if one exists.
    """
    result = SOURCES.find({"sc_id": sc_id})
    if result.count() != 0:
        return result



def add_song_to_source(song_data,sourceID):
    """
    Song is a dictionary returned from the scraper. Song is added if does
    not already exist in the db under the specified streamURL.
    """
    if not song_data:
        return
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
            # print "DB: Song already exists in specified source, skipping."
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

def add_source_to_db(source_url, title, rss_url=""):
    source = SOURCES.insert({"source_url": source_url, "title":title,"rss_url":rss_url,
                            "songs": [], "users":[]})
    if source:
        return source
    else:
        print "Unable to add source url:",source_url,"to db"

def add_sc_user_to_db(sc_id,username):
    """
    Adds sc user to db.
    """
    print sc_id,"DB: SC_ID"
    source = SOURCES.insert({"sc_id":sc_id,"username":username,"songs": [], "users":[]})
    if source:
        return source
    else:
        print "Unable to add sc source:",sc_id,"to db"

# def add_songs_to_sc_source(songs,sourceID):
#     """
#     Adds all the sc songs in the array 'songs' of soundcloud objects to 
#     the sourceID db entry.
#     """
#     sc_user = get_sc_source_by_sc_id(sc_id)
#     if not sc_user:
#         return 

#     opt_fields = ["_id","title", "genre", "streamURL", "artworkURL", "date","artist"]
#     for s in songs:
#         print s
#         song = {k: s.get(k) for k in opt_fields}

#         # add the sourceID to the song
#     song["sourceID"] = ObjectId(sourceID)

#     # retrieve the source by sourceID
#     result = SOURCES.find({"_id": sourceID})
#     if result.count() == 0:
#         print "DB: ",sourceID,"not found, unable to add song:",song
#         return

#     # change the artwork url to larger size
#     aurl = song.get("artworkURL")
#     if aurl:
#         song["artworkURL"] = aurl.replace("-large","-t500x500")

#     source_songs = result[0]["songs"]
#     for i in source_songs:
#         if i["streamURL"] == song["streamURL"]:
#             # print "DB: Song already exists in specified source, skipping."
#             return

#     source_songs.append(song)
#     query = {"songs":source_songs}
#     if SOURCES.update({'_id':ObjectId(sourceID)},{"$set":query},upsert=False):
#         return True
#     else:
#         print "DB: Unable to add song:",song_data.get("_id"),"to source:",sourceID

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
    GROUPS.drop()
