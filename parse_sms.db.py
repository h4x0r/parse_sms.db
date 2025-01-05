#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_sms.db.py - Parse sms.db from iOS

Author: Albert Hui <albert@securityronin.com>
"""
__updated__ = '2025-01-05 22:30:54'

from argparse import ArgumentParser, Namespace
from pathlib import Path
import sys
import sqlite3 
from datetime import datetime, timezone
import plistlib
import typedstream
import zipfile

class color:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

def macAbsTimeToUnixTime(macAbsoluteTime):
	# Normalize nanoseconds to seconds
	if macAbsoluteTime > 0xFFFFFFFF:
		macAbsoluteTime = macAbsoluteTime / 1e9

	# Mac absolute time is from 2001-01-01, Unix time is from 1970-01-01
	return macAbsoluteTime + 978307200

def unixTimeToString(unixTime):
	return datetime.fromtimestamp(unixTime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def openSQLiteDB(db):
	try:
		conn = sqlite3.connect(db)
		return conn
	except sqlite3.Error as e:
		print(f"Error opening sms.db file: {e}")
		return None

def parseArgs(cliArgs: list[str] = None) -> Namespace: # None means sys.argv[1:]
	parser = ArgumentParser()
	parser.add_argument("file", help="sms.db file, usually located in /private/var/mobile/Library/SMS/sms.db")
	return parser.parse_args(args=cliArgs)

def main(args: Namespace = parseArgs()) -> int:
	file = Path(args.file)
	if not file.is_file():
		print(f'File {args.file} does not exist')
		raise SystemExit(1)
	if zipfile.is_zipfile(file):
		with zipfile.ZipFile(file, 'r') as zip_ref:
			for file_name in zip_ref.namelist():
				if file_name.endswith('sms.db'):
					file = zip_ref.extract(file_name,path='/tmp')
					break

	conn = openSQLiteDB(file)
	conn.row_factory = sqlite3.Row
	c = conn.cursor() 
	statement = '''SELECT * FROM message m, handle h WHERE m.handle_id = h.ROWID ORDER BY m.ROWID'''
	c.execute(statement) 

	print("Row Gap,ROWID,From/To,Counterparty,Service,Sent/Scheduled Time,Text,Read Time,Edited Time,Edited Text")
	lastrowid = 0
	for row in c.fetchall():
		rowid = row['ROWID']
		rowiddiff = rowid - lastrowid - 1
		rowgap = color.WARNING + f"[❌ row gap: {rowiddiff} rows missing]" + color.ENDC if rowiddiff > 0 else ''
		lastrowid = rowid

		fromto = "To" if row['is_from_me'] == 1 else "From"
		id = row['id'] # handle.id
		service = row['service']
		date = unixTimeToString(macAbsTimeToUnixTime(row['date']))
		text = f'"{row['text']}"' if row['text'] is not None else ''
		if row['date_read']:
			date_read = unixTimeToString(macAbsTimeToUnixTime(row['date_read']))
		else:
			if row['is_read'] == 1:
				date_read = '[📭 read but read time data not available]'
			else:
				match row['service']:
					case "SMS" | "MMS": # read receipts not supported
						date_read = '[❔ not known if read or not: messaging service does not support read receipt]'
					case "iMessage" | "RCS": # read receipts supported
						date_read = '[📬 unread]'
					case _: # unknown (future) messaging service
						date_read = f'[❔ not known if read or not: {row['service']} not supported]'

		date_edited = unixTimeToString(macAbsTimeToUnixTime(row['date_edited'])) if row['date_edited'] else ''
		text_edited = ''

		if date_edited != '' and text == '':
			# edited message with no original text
			text = color.WARNING + '[🧹 cleared upon unsent]' + color.ENDC
			text_edited = color.WARNING + '[⏮️ unsent]' + color.ENDC

		# parse original and edited texts from message_summary_info
		if row['message_summary_info'] is not None:
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
							text = f'"{v.value}"'
							break
				# edited text
				ts = typedstream.unarchive_from_data((((message_summary_info['ec'])['0'])[1])['t'])
				for c in ts.contents:
					for v in c.values:
						# check if v has the property 'archived_name'
						if not (hasattr(v, 'archived_name') and hasattr(v, 'value')):
							continue
						if (v.archived_name == b'NSMutableString' or v.archived_name == b'NSString') and v.value is not None:
							text_edited = f'"{v.value}"'
							break

		print(f'{rowgap},{rowid},{fromto},"{id}",{service},{date},{text},{date_read},{date_edited},{text_edited}')

	conn.commit()
	conn.close()

	return 0 # success

if __name__ == "__main__":
    sys.exit(main(parseArgs()))