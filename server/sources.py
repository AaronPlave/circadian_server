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

def add_source(source_url,user_id):
    result = db.get_source_by_url(source_url)
    if result:
        return db.format_songs(result[0]["songs"])
    # else scrape the source and if successful add source and songs
    # to db and add the source to the user.
    pool = multiprocessing.Pool(1)
    success = pool.map(scraping.scrape_new_source,[[source_url,user_id]])
    if success[0]:
        return db.get_source_by_url(source_url)[0]["songs"]

def refresh_handler():
    print "Starting source refresh process"
    pool = multiprocessing.Pool(1)
    pool.map_async(refresh_sources,())

def refresh_sources():
    SLEEP_TIME = 10 #sleep 10 seconds

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
    refresh_sources()

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
        'http://abeano.com','http://potholesinmyblog.com',
        'http://prettymuchamazing.com','http://disconaivete.com',
        'http://doandroidsdance.com','http://www.npr.org/blogs/allsongs/',
        'http://blogs.kcrw.com/musicnews/']

    print "TEST: scraping sources"
    [add_source(i,"1") for i in blogs[0:2]]


    
    # #add a source to user
    s = db.list_sources()[0]["_id"]
    # print "TEST:",s,"source to add" 
    # print "TEST: adding a source to user '1' "
    # db.add_source_to_user(s,"1")

    print "TEST: verifying user has that source"
    print "TEST: User has source:",s in db.get_user("1")[0]["sources"]
    
    print "TEST: getting user's songs"
    return db.get_user_songs("1")
