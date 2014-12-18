"""
Adding Source Steps:
1: Check sources db to see if source already exists, if it does, return
	success along with all of the source's songs.
2: Otherwise, attempt to scrape from the source. If successful, add the source
	to sources db and return success + source's songs. If scrape fails, return
	failure.
"""

import db

def add_source(source):
	return source
