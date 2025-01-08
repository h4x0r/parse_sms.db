# parse_smsdb

Extracts iMessage, RCS, SMS/MMS chat history from iOS database file.

![parse_smsdb sreenshot](https://github.com/h4x0r/parse_sms.db/blob/main/screenshot.png)

## Description

This tool parses sms.db originated from iOS devices and outputs a CSV (common-separated value) table with annotations useful for forensic examination.

Features:
- Highlight row gaps (indicative of deletions)
- Annotate unsent messages
- Flattens edited message data on to root table for easy review
- Output message read time and annotate unread messages (for services supporting read receipts)

## Getting Started

### Prerequisites

* Python

### Installation

1. Install from PyPI
```
pip install parse_smsdb
```

## Usage

* Parse sms.db
```
parse_smsdb 'private/var/mobile/Library/SMS/sms.db'
```

* Parse sms.db within a .zip archive
```
parse_smsdb 'IACIS Certified Mobile Device Examiner (ICMDE)/03 iOS/iOS Files/Evidence/506 - Editing SMS iOS 16.zip'
```

## Version History

* 0.1.0
	* Initial release

## Contact

[Albert Hui](https://www.linkedin.com/in/alberthui) | [albert@securityronin.com](mailto:albert@securityronin.com) | [@4n6h4x0r.bsky.social](https://bsky.app/profile/4n6h4x0r.bsky.social)

Project Link: [https://github.com/h4x0r/parse_sms.db](https://github.com/h4x0r/parse_sms.db)

## Acknowledgments

* [IACIS MDF Training Course](https://www.iacis.com/training/mobile-device-forensics/) and [Jung Son](https://www.linkedin.com/in/jungson/)'s teaching
* [Magnet Forensic](https://www.magnetforensics.com/)'s blog posts: [The Meaning of Messages](https://www.magnetforensics.com/blog/the-meaning-of-messages/), and [A look into iOS 18's changes](https://www.magnetforensics.com/blog/a-look-into-ios-18s-changes/)
