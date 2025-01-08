#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4 noexpandtab
"""
parse_smsdb.py -  Extracts iMessage, RCS, SMS/MMS chat history from iOS database file.

Author: Albert Hui <albert@securityronin.com>
"""
import importlib.metadata
__updated__ = '2025-01-08 21:17:17'

def version_callback(value: bool):
	if value:
		distributions = importlib.metadata.distributions()
		__version__ = '[not installed]'
		for dist in distributions:
			args = (dist.metadata['Name'], dist.version)
			if args[0] == 'parse-smsdb':
				__version__ = args[1]
				break
		print(f'{__version__} build {__updated__}')
		raise typer.Exit()

import typer
from typing_extensions import Annotated, Optional
from pathlib import Path
import tempfile
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

def mac_abs_time_to_unix_time(mac_abs_time):
	# Normalize nanoseconds to seconds
	if mac_abs_time > 0xFFFFFFFF:
		mac_abs_time = mac_abs_time / 1e9

	# Mac absolute time is from 2001-01-01, Unix time is from 1970-01-01
	return mac_abs_time + 978307200

def unix_time_to_string(unixTime):
	return datetime.fromtimestamp(unixTime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def open_sqlite_db(db):
	try:
		conn = sqlite3.connect(db)
		return conn
	except sqlite3.Error as e:
		print(f"Error opening sms.db file: {e}")
		raise SystemExit(1)

def parse_smsdb(
    file: Annotated[str, typer.Argument(help="sms.db file from iOS file system at /private/var/mobile/Library/SMS/, or zip file containing sms.db")] = "sms.db",
	version: Annotated[ Optional[bool], typer.Option("--version", callback=version_callback, help="Show version.") ] = None,
):
	f = Path(file)
	if not f.is_file():
		print(f'File does not exist')
		raise SystemExit(1)

	with tempfile.TemporaryDirectory() as temp_dir:
		if zipfile.is_zipfile(f):
			with zipfile.ZipFile(file, 'r') as zip_ref:
				for file_name in zip_ref.namelist():
					if file_name.endswith('sms.db'):
						f = zip_ref.extract(file_name,path=temp_dir)
						break
			if f == Path(file):
				print(f'Zip file does not contain an sms.db')
				raise SystemExit(1)

		conn = open_sqlite_db(f)
		conn.row_factory = sqlite3.Row
		c = conn.cursor() 
		statement = '''SELECT * FROM message m, handle h WHERE m.handle_id = h.ROWID ORDER BY m.ROWID'''
		try:
			c.execute(statement) 
		except sqlite3.DatabaseError as e:
			print(f"Error executing SQL statement: {e}")
			raise SystemExit(1)

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
			date = unix_time_to_string(mac_abs_time_to_unix_time(row['date']))
			text = f'"{row['text']}"' if row['text'] is not None else ''
			if row['date_read']:
				date_read = unix_time_to_string(mac_abs_time_to_unix_time(row['date_read']))
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

			date_edited = ''
			text_edited = ''

			if 'date_edited' in row.keys():
				date_edited = unix_time_to_string(mac_abs_time_to_unix_time(row['date_edited'])) if row['date_edited'] else ''

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

def main():
	typer.run(parse_smsdb)

if __name__ == "__main__":
	main()
