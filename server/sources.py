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
from collections import Counter
import random
import sc_lib

REFRESH_WAIT_MINUTES = 15 


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
    print source
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
    data = {"error":""}
    result = db.get_source_by_url(source_url)

    if result:
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
    if success[0] == "good":
        result = db.get_source_by_url(source_url)
        if result:
            return format_add_result(result[0],data)

    data["error"] = success[0]
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


def refresh_sources(x):
    SLEEP_TIME = REFRESH_WAIT_MINUTES*60  #convert to seconds
    sources = db.SOURCES.find()

    if sources.count() == 0:
        print "REFRESHER: NO SOURCES FOUND, WAITING"
        time.sleep(SLEEP_TIME)
        refresh_sources()
    print "REFRESHER: SCRAPING SONGS"
    sources_to_scrape = [(i["_id"],i["rss_url"]) for i in sources]
    print sources_to_scrape
    [scraping.scrape_current_source(i) for i in sources_to_scrape]
    print "REFRESHER: SCRAPED SOURCES"
    print "REFRESHER: BUILDING RECOMMENDATIONS"
    recs_built = build_recommendations()
    if not recs_built:
        print "REFRESHER: FAIL: UNABLE TO BUILD RECOMMENDATIONS"
    print "REFRESHER: SUCCESSFULY SCRAPED SOURCES AND BUILT RECS, SLEEPING"
    time.sleep(SLEEP_TIME)
    refresh_sources(x)

def refresh_handler():
    print "REFRESH HANDLER: Starting source refresh process"
    pool = multiprocessing.Pool(1)
    pool.map_async(refresh_sources,("0"))

def test():
    """
    Simulates stuff
    """
    #clear sources
    print "TEST: dropping db"
    db.SOURCES.drop()

    #clear users
    print "TEST: dropping users"
    db.USERS.drop()

    print "TEST: adding user '1' "
    db.add_user("1")
    
    print "TEST: verifying user 1 is in db"
    if not db.get_user("1"):
        print "TEST: No user '1' found"
        return False
    print "TEST: found user 1"

    # Add source
    blogs = ["http://thissongissick.com",
        "http://eqmusicblog.com",'http://gorillavsbear.net',
        'http://potholesinmyblog.com', 'http://prettymuchamazing.com',
        'http://disconaivete.com', 'http://doandroidsdance.com',
        'http://www.npr.org/blogs/allsongs/','http://blogs.kcrw.com/musicnews/',
        "http://www.edmsauce.com"]

    # blogs = ["http://www.npr.org/blogs/allsongs/"]

    print "TEST: scraping sources"
    results = [add_blog_source(i,"1") for i in blogs]

    # stop test if no sources succeeded
    cont = False
    for i in results:
        if i:
            cont = True
            continue 
    if not cont:
        "TEST: No sources succeeded, unable to continue test." 
        return False

    # add a source to user
    s = db.list_sources()[0]["_id"]

    print "TEST: verifying user has that source"
    print "TEST: User has source:",s in db.get_user("1")[0]["sources"]
    
    print "TEST: getting user's songs"
    return db.get_user_songs("1")



def test3():
    print "TEST: dropping all DBs"
    db.remove_all()

    print "TEST: adding users"
    NUM_USERS = 10
    users = [str(i) for i in range(NUM_USERS)]
    add_user_result = reduce(lambda x,y: x and y, [db.add_user(i) for i in users])
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
    db.add_user("some_person")

    print "TEST: getting recommendations"
    print build_recommendations()
    return ""
