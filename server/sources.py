"""
Adding Source Steps:
1: Check sources db to see if source already exists, if it does, return
    success along with all of the source's songs.
2: Otherwise, attempt to scrape from the source. If successful, add the source
    to sources db and return success + source's songs. If scrape fails, return
    failure.
"""

import db
from bson.json_util import dumps
import multiprocessing
import scraping

some_queue = ["?"]

def add_source(source_url,user_id):
    # THIS IS NOT FUNCTIONING ANY DIFFERENTLY FROM
    # OTHER SOURCES AT THE MOMENT.. SHOULD JUST SCRAPE THAT
    # ONE SOURCE!
    result = db.get_source_by_url(source_url)
    if result:
        return dumps(result)
    # else add and trigger a scrape
    db.add_source_to_db(source_url)
    refresh_sources()

def refresh_sources():
    sources = db.SOURCES.find()
    if sources.count() == 0:
        print "No sources, nothing to scrape."
        return
    sources_to_scrape = [(i["source_url"],i["_id"],i["rss_url"]) for i in sources]
    print sources_to_scrape
    count = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(count)
    output = pool.map(scraping.scrape_source,sources_to_scrape)
    print output

import time
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

    # Add source
    blogs = ["http://thissongissick.com/blog/#sthash.4oplcVTM.dpbs",
        "http://eqmusicblog.com/",'http://gorillavsbear.net',
        'http://abeano.com','http://potholesinmyblog.com',
        'http://prettymuchamazing.com','http://disconaivete.com',
        'http://doandroidsdance.com','http://www.npr.org/blogs/allsongs/',
        'http://blogs.kcrw.com/musicnews/']
    print "TEST: adding sources to db"
    [db.add_source_to_db(i) for i in blogs[0:1]]

    print "TEST: refreshing sources"
    refresh_sources()

    # print "TEST: sleeping for 4 to wait..."
    # time.sleep(4)

    print "TEST: adding user '1' "
    db.add_user("1")

    print "TEST: verifying user 1 is in db"
    if not db.get_user("1"):
        print "TEST: No user '1' found"
        return False
    print "TEST: found user 1"
    
    #add a source to user
    s = db.list_sources()[0]["_id"]
    print "TEST:",s,"source to add" 
    print "TEST: adding a source to user '1' "
    db.add_source_to_user(s,"1")

    print "TEST: verifying user has that source"
    print "TEST: User has source:",s in db.get_user("1")[0]["sources"]
    
    print "TEST: getting user's songs"
    return db.get_user_songs("1")