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

def get_most_popular_sources(limit=15):
    """
    Returns the list of sources ranked by number of subscribers.
    """
    print "getting most"
    return list(db.SOURCES.find(limit=limit).sort([('users',db.pymongo.DESCENDING)]))

def get_user_recommendations(user_id):
    """
    Oh boy. Gets recommendations for user based off other users who share
    the same sources.
    """
    user = db.get_user(user_id)
    if not user:
        print "User not found, no recommendations"
        return []
    user_sources = user[0]["sources"]
    if not user_sources:
        print "User has no sources"
        return get_most_popular_sources()
    
    other_sources = {}
    for s in user_sources:
        tmp_source = db.get_source_by_id(s)
        if not tmp_source:
            print "SOURCES: Unable to find source in get rec, skipping"
            continue
        source_users = tmp_source[0]["users"]
        for u in source_users:
            # if u == current user, skip
            if u == user[0]["user_id"]:
                print u, user[0]["user_id"],len(source_users)
                print "REC: Skipping this source user, same as primary user"
                continue
            print "REC: But wait!"
            tmp_user = db.get_user(u)
            if not tmp_user:
                print "REC: Unable to find source user, skipping"
                continue 
            other_user_sources = tmp_user[0]["sources"]
            print "REC: Other user's sources:",other_user_sources
            for j in other_user_sources:
                if j not in user_sources:
                    if j in other_sources:
                        other_sources[j] += 1
                    else:
                        other_sources[j] = 1

    # if after all that we have no recommendations or we don't have many,
    # just get most popular sources
    if len(other_sources) < 1:
        return get_most_popular_sources()

    # otherwise, go get the sources
    final_recommendations = []
    for i in other_sources:
        curr_source = db.get_source_by_id(db.ObjectId(i))
        if not curr_source:
            print "REC: Failed to get curr_source"
            continue
        final_recommendations.append(curr_source[0])
    print final_recommendations
    return final_recommendations


def format_add_result(source,data):
    songs_raw = source["songs"]
    songs = db.format_ids(songs_raw)
    source["songs"] = songs
    data["source"] = source
    data["source"]["_id"] = str(data["source"]["_id"]) 

    # change source_url to sourceURL
    data["source"]["sourceURL"] = data["source"]["source_url"]
    del data["source"]["source_url"]
    del data["source"]["rss_url"]

    data["source"]["title"] = data["source"]["sourceURL"]
    
    return data

def format_source_result(source):
    # format the songs
    songs_raw = source["songs"]
    songs = db.format_ids(songs_raw)
    source["songs"] = songs

    # change source_url to sourceURL
    source["sourceURL"] = source["source_url"]
    del source["source_url"]
    del source["rss_url"]

    source["title"] = source["sourceURL"]

   # turn the source object id into a string 
    source["_id"] = str(source["_id"])

    # replace 'users' with 'subscriberCount'
    source["subscriberCount"] = len(source["users"])
    del source["users"]
    return source 

def add_source(source_url,user_id):
    data = {"error":""}
    result = db.get_source_by_url(source_url)

    if result:
        # add user to source and source to user
        print result
        if db.link_source_and_user(result[0]["_id"],user_id):
            return format_add_result(result[0],data)
        else:
            print "SOURCES: Unable to link source and user"
            data['error'] = 'server'
            return data

    # else scrape the source and if successful add source and songs
    # to db and add the source to the user.
    print "DONT HAVE SOURCE YET, SCRAPING:",source_url
    pool = multiprocessing.Pool(1)
    success = pool.map(scraping.scrape_new_source,[[source_url,user_id]])
    #result will either be 'good' for no problems, 'user' for an unreachable
    # url, or 'server' if we can't find an RSS link.
    print "RESULT OF SCRAPING:",success 
    if success[0] == "good":
        result = db.get_source_by_url(source_url)
        if result:
            return format_add_result(result[0],data)

    data["error"] = success[0]
    return data

def refresh_sources(x):
    SLEEP_TIME = 1*60 #sleep 10 seconds
    sources = db.SOURCES.find()

    if sources.count() == 0:
        print "REFRESHER: NO SOURCES FOUND, WAITING"
        time.sleep(SLEEP_TIME)
        refresh_sources()
    print "REFRESHER: SCRAPING SONGS"
    sources_to_scrape = [(i["source_url"],i["_id"],i["rss_url"]) for i in sources]
    [scraping.scrape_current_source(i) for i in sources_to_scrape]
    print "REFRESHER: SCRAPED SOURCES"
    time.sleep(SLEEP_TIME)
    refresh_sources(x)

def refresh_handler():
    print "Starting source refresh process"
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
    results = [add_source(i,"1") for i in blogs]

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


import random
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
        if not add_source(blogs[i],users[i]):
            print "TEST: FAIL: ADDING SOURCE TO USER"


    # add same sources to different users a bunch of times
    for j in range(7):
        random.shuffle(users)
        for i in range(len(blogs)):
            if not add_source(blogs[i],users[i]):
                print "TEST: FAIL: ADDING SOURCE TO USER"

    print "TEST: getting recommendations"
    return get_user_recommendations("2")
