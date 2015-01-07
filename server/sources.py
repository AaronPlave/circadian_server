"""
Adding Source Steps:
1: Check sources db to see if source already exists, if it does, return
    success along with all of the source's songs.
2: Otherwise, attempt to scrape from the source. If successful, add the source
    to sources db and return success + source's songs. If scrape fails, return
    failure.
"""
import db
import time
import multiprocessing
import scraping
import random
import sc_lib
from pyapns.apns import APNs, Frame, Payload
from collections import Counter

REFRESH_WAIT_MINUTES = 15

apns = APNs(use_sandbox=False,cert_file='cert.pem',key_file='key.pem')


def get_most_popular_sources(user_sources):
    """
    Returns the list of sources ranked by number of subscribers that are
    not in the set of sources owned by 'user'.
    """
    sources = db.SOURCES.find().sort([('users',db.pymongo.DESCENDING)])
    final_sources = []
    for i in sources:
        if i not in user_sources:
            final_sources.append(i["_id"])
    return final_sources

def build_user_recommendations(user_id):
    """
    Oh boy. Gets recommendations for user based off other users who share
    the same sources.
    """
    NUM_RECOMMENDATIONS = 1
    user = db.get_user(user_id)
    if not user:
        print "REC: ERROR: User not found, no recommendations"
        return []
    user_sources = user[0]["sources"]

    if not user_sources:
        other_sources = get_most_popular_sources(user_sources)
        return db.update_user_recommendations(user_id,other_sources)

    other_sources = Counter()
    for s in user_sources:
        tmp_source = db.get_source_by_id(s)
        if not tmp_source:
            continue
        source_users = tmp_source[0]["users"]
        for u in source_users:
            if u == user[0]["user_id"]:
                continue
            tmp_user = db.get_user(u)
            if not tmp_user:
                continue 
            other_user_sources = tmp_user[0]["sources"]
            for j in other_user_sources:
                if j not in user_sources:
                        # if j not in other_sources it will automatically be 0
                        other_sources[j] += 1

    # if after all that we have no recommendations or we don't have many,
    # just get most popular sources
    other_sources = [i[0] for i in other_sources.most_common()]
    if len(other_sources) < NUM_RECOMMENDATIONS:
        other_sources = get_most_popular_sources(user_sources)
    # update user recs and return the db add query boolean.   
    return db.update_user_recommendations(user_id,other_sources)

def build_recommendations():
    """
    Builds recommendations for each user in the db. If any fail, return False.
    """
    success = True
    for u in db.USERS.find():
        success = build_user_recommendations(u["user_id"])
    return success

def format_add_result(source,data):
    songs_raw = source["songs"]
    songs = db.format_ids(songs_raw)
    source["songs"] = songs
    data["source"] = source
    data["source"]["_id"] = str(data["source"]["_id"]) 

    # change source_url to sourceURL
    if data["source"].get("source_url"):
        data["source"]["sourceURL"] = data["source"]["source_url"]
        del data["source"]["source_url"]
        del data["source"]["rss_url"]

    if data["source"].get("sc_id"):
        data["source"]["title"] = data["source"]["username"]
        data["source"]["sourceID"] = data["source"]["sc_id"]
        del data["source"]["username"]
        del data["source"]["sc_id"]
    print "DATA",data
    return data

def format_source_result(source):
    # format the songs
    songs_raw = source["songs"]
    songs = db.format_ids(songs_raw)
    source["songs"] = songs

    # change source_url to sourceURL
    if source.get("source_url"):
        source["sourceURL"] = source["source_url"]
        del source["source_url"]
        del source["rss_url"]

    if source.get("sc_id"):
        source["title"] = source["username"]
        source["sourceID"] = source["sc_id"]
        del source["username"]
        del source["sc_id"]

   # turn the source object id into a string 
    source["_id"] = str(source["_id"])

    # replace 'users' with 'subscriberCount'
    source["subscriberCount"] = len(source["users"])
    del source["users"]
    return source 

def add_blog_source(source_url,user_id):
    print "DB: adding blog source"
    data = {"error":""}
    result = db.get_source_by_url(source_url)
    if result:
        print "GOT CACHED"
        # add user to source and source to user
        if db.link_source_and_user(result[0]["_id"],user_id):
            return format_add_result(result[0],data)
        else:
            print "SOURCES: Unable to link source and user"
            data['error'] = 'server'
            return data

    # else scrape the source and if successful add source and songs
    # to db and add the source to the user.
    pool = multiprocessing.Pool(1)
    success = pool.map(scraping.scrape_new_source,[[source_url,user_id]])
    #result will either be 'good' for no problems, 'user' for an unreachable
    # url, or 'server' if we can't find an RSS link.
    print success, "SUCC"
    if success[0][0] == "good":
        sourceID = success[0][1]
        result = db.get_source_by_id(sourceID)
        print "RESULT:",result
        if result:
            print result,"!"
            return format_add_result(result[0],data)

    data["error"] = success[0][0]
    # print data,"DATA"
    return data

def add_sc_source(sc_id, user_id):
    data = {"error":""}
    result = db.get_sc_source_by_sc_id(sc_id)

    if result:
        # add user to source and source to user
        if db.link_source_and_user(result[0]["_id"],user_id):
            return format_add_result(result[0],data)
        else:
            print "SOURCES: Unable to link source and user"
            data['error'] = 'server'
            return data

    # else validate the new sc source and if exists, add source and songs
    # to db and add the source to the user.
    pool = multiprocessing.Pool(1)
    success = pool.map(sc_lib.validate_new_user,[[sc_id,user_id]])
    #result will either be 'good' for no problems, 'user' for a bad sc_id
    # ,or 'server' if something else is broken.
    if success[0] == "good":
        # success[1] will be the mongo id of the new source
        result = db.get_sc_source_by_sc_id(sc_id)
        if result:
            return format_add_result(result[0],data)

    data["error"] = success[0]
    return data

def group_notification(user_id,groupID):
    """
    Sends a notification to the users in a group (except the origin user).
    """
    # get the group
    grp = db.GROUPS.find({"_id":db.ObjectId(groupID)})
    if grp.count() == 0:
        print "SOURCES: Could not find group:",groupID,"in send_notification"
        return False
    grp_users = grp[0]["users"]
    if not grp_users:
        return True

    # remove user_id from grp_users
    if user_id in grp_users:
        grp_users.remove(user_id)
    else:
        print "SOURCES: Uh oh, user_id not in the group it's supposed to be in..."
        return False
  
    # get all in the group
    users = db.USERS.find({"user_id":{"$in":grp_users}})
    if users.count() == 0:
        print "SOURCES: No other users in group besides sender, not notifying."
        return True
    if users.count() != len(grp_users):
        print "SOURCES: Did not find all the users in the group, CONCERN!"

    # get list of device tokens to send a message to
    deviceTokens = []
    for i in users:
        deviceTokens.extend(i["deviceTokens"])

    # send notification to all of the users
    frame = Frame()
    identifier = 1
    expiry = time.time()+3600
    priority = 10
    payload = Payload(alert="Hello World!", sound="default", badge=1)
    for i in deviceTokens:
        frame.add_item(deviceTokens, payload, identifier, expiry, priority)
    apns.gateway_server.send_notification_multiple(frame)
    print "SOURCES: Send multiple notifications."
    return True

def refresh_sources(x):
    SLEEP_TIME = REFRESH_WAIT_MINUTES*60  #convert to seconds
    sources = db.SOURCES.find()

    if sources.count() == 0:
        print "REFRESHER: NO SOURCES FOUND, WAITING"
        time.sleep(SLEEP_TIME)
        refresh_sources()

    try:
        print "REFRESHER: SCRAPING SONGS"
        sources_to_scrape = [(i["_id"],i["rss_url"]) for i in sources]
        print sources_to_scrape
        [scraping.scrape_current_source(i) for i in sources_to_scrape]
        print "REFRESHER: SCRAPED SOURCES"
    except Exception, e:
        print "REFRESHER: Failed to scrape sources, error:",e

    print "REFRESHER: BUILDING RECOMMENDATIONS"
    try:
        recs_built = build_recommendations()
        if not recs_built:
            print "REFRESHER: FAIL: UNABLE TO BUILD RECOMMENDATIONS"
    except Exception,e:
        print "REFRESHER: Failed to build recommendations, error:",e
    
    print "REFRESHER: CLEARING OLD SONGS"
    old_songs_removed = db.remove_old_songs()
    if not old_songs_removed:
        print "REFRESHER: FAILED TO REMOVE OLD SONGS FROM DB."

    old_group_songs_removed = db.remove_old_group_songs()
    if not old_group_songs_removed:
        print "REFRESHER: FAILED TO REMOVE OLD GROUP SONGS FROM DB."
    
    print "REFRESHER: SUCCESSFULY SCRAPED SOURCES, BUILT RECS, CLEANED DB OF OLD SONGS AND GROUP SONGS, SLEEPING"
    time.sleep(SLEEP_TIME)
    refresh_sources(x)


def refresh_handler():
    print "REFRESH HANDLER: Starting source refresh process"
    pool = multiprocessing.Pool(1)
    pool.map_async(refresh_sources,("0"))

def test3():
    print "TEST: dropping all DBs"
    db.remove_all()

    print "TEST: adding users"
    NUM_USERS = 10
    users = [str(i) for i in range(NUM_USERS)]
    add_user_result = reduce(lambda x,y: x and y, [db.add_user(i,"asdasdas","some name"+str(i),[]) for i in users])
    if not add_user_result:
        print "TEST: FAIL: ADD USERS"

    print "TEST: adding blogs"
    blogs = ["http://thissongissick.com",
        "http://eqmusicblog.com",'http://gorillavsbear.net',
        'http://potholesinmyblog.com', 'http://prettymuchamazing.com',
        'http://disconaivete.com', 'http://doandroidsdance.com',
        'http://www.npr.org/blogs/allsongs/','http://blogs.kcrw.com/musicnews/',
        "http://www.edmsauce.com"]

    # add sources
    for i in range(len(blogs)):
        if not add_blog_source(blogs[i],users[i]):
            print "TEST: FAIL: ADDING SOURCE TO USER"


    # add same sources to different users a bunch of times
    for j in range(7):
        random.shuffle(users)
        random.shuffle(blogs)
        for i in range(len(blogs)):
            if not add_blog_source(blogs[i],users[i]):
                print "TEST: FAIL: ADDING SOURCE TO USER"


    print "TEST: adding new user to test for no sources"
    db.add_user("some_person","asdasdas","some name",[])

    print "TEST: getting recommendations"
    print build_recommendations()
    return "test3 passed"
