#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_sms.db.py - Parse sms.db from iOS, supports edited messages

Author: Albert Hui <albert@securityronin.com>
"""
__updated__ = '2024-12-31 16:08:25'

import os
import sqlite3 
from datetime import datetime
import pytz
import plistlib
import typedstream

def macAbsTimeToUnixTime(macAbsoluteTime):
	# Normalize nanoseconds to seconds
	if macAbsoluteTime > 0xFFFFFFFF:
		macAbsoluteTime = macAbsoluteTime / 1e9

	# Mac absolute time is from 2001-01-01, Unix time is from 1970-01-01
	return macAbsoluteTime + 978307200

def unixTimeToString(unixTime):
	return datetime.fromtimestamp(unixTime,pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S UTC')

def openSQLiteDB(db):
	try:
		if not os.path.exists(db):
			print(f"Database {db} does not exist")
			exit(1)
		conn = sqlite3.connect(db)
		return conn
	except sqlite3.Error as e:
		print(f"Error opening database: {e}")
		return None

conn = openSQLiteDB('sms.db')
conn.row_factory = sqlite3.Row
c = conn.cursor() 
statement = '''SELECT * FROM message m, handle h WHERE m.handle_id = h.ROWID ORDER BY m.ROWID'''
c.execute(statement) 

print("ROWID,From/To,Counterparty,Service,Original Time,Original Text,Edited Time,Edited Text")
for row in c.fetchall():
	ROWID = row['ROWID']
	fromto = "To" if row['is_from_me'] == 1 else "From"
	id = row['id'] # handle.id
	service = row['service']
	date = unixTimeToString(macAbsTimeToUnixTime(row['date']))
	text = f"'{row['text']}'" if row['text'] is not None else ''
	date_edited = unixTimeToString(macAbsTimeToUnixTime(row['date_edited'])) if row['date_edited'] else ''
	text_edited = f"''"

	if date_edited != '' and text == '':
		# edited message with no original text
		text = '[deleted]'
		text_edited = '[unsent]'

	# parse original and edited texts from message_summary_info
	if row['message_summary_info'] is None:
		continue
	message_summary_info = plistlib.loads(row['message_summary_info'])
	if 'ec' in message_summary_info and '0' in message_summary_info['ec']:
		# original text
		ts = typedstream.unarchive_from_data((((message_summary_info['ec'])['0'])[0])['t'])
		for c in ts.contents:
			for v in c.values:
				# check if v has the property 'archived_name'
				if not (hasattr(v, 'archived_name') and hasattr(v, 'value')):
					continue
				if (v.archived_name == b'NSMutableString' or v.archived_name == b'NSString') and v.value is not None:
					text = f"'{v.value}'"
					break
		# edited text
		ts = typedstream.unarchive_from_data((((message_summary_info['ec'])['0'])[1])['t'])
		for c in ts.contents:
			for v in c.values:
				# check if v has the property 'archived_name'
				if not (hasattr(v, 'archived_name') and hasattr(v, 'value')):
					continue
				if (v.archived_name == b'NSMutableString' or v.archived_name == b'NSString') and v.value is not None:
					text_edited = f"'{v.value}'"
					break

	print(f"{ROWID},{fromto},'{id}',{service},{date},{text},{date_edited},{text_edited}")

conn.commit()
conn.close()