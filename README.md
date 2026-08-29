# Tiktok export followers and following list
Export Tiktok followers and following list to json file and Excel

**getInfosAccounts.py :** get id and creation date of Tiktok accounts<br/>
**get-follows-details.py** : export followers or following list of Tiktok accounts

For a list of Tiktok accounts, get their followers/following list (maximum : last 10000 follows) with their infos.<br />
Results are saved in a .json and .xlsx file.

# Installation

Install Python then all required modules.
```python
pip3 install curl_cffi beautifulsoup4 pandas
```

# Usage
## 1- getInfosAccounts.py : Get numeric id of Tiktok account
First, for each Tiktok account you want their follower/following list, get their numeric id.<br />
Edit getInfosAccounts.py and input accounts name list at the end of script.<br />
Example : ```accounts = ["singularynapse"]```<br />
Run getInfosAccounts.py, it will display : ```singularynapse : 6863874874285622278 created on 2021-07-29 20:03:48```<br />
```6863874874285622278``` is numeric id of tiktok.com/@singularynapse account

## 2- get-follows-details.py : Export followers/following list of Tiktok accounts id
First, setup get-follows-details.settings.json with all accounts ids you want to export and what list to scrape (```"followers"``` or ```"following"```)<br />
As some accounts aren't accessible without being connected to Tiktok, you'll have better results if you have a Tiktok account.<br />
Connect to your Tiktok account and get your "sessionid_ss" and "tt-target-idc" cookies value, then set them in get-follows-details.settings.json<br />
Some settings concern waiting after each step and account, after each error, etc...<br />
Example :
```json
{"accounts": [
	{"id": "6863874874285622278", "steps": {"stepGetFollows": true, "stepGetFollowsDetails": true, "stepConvertJsonToExcel": true}}
],
"scrape": "followers",
...
"httpRequest": {
	"verifySSL": true,
	"cookies": {"sessionid_ss": "from cookies when connected to Tiktok", "tt-target-idc": "from cookies when connected to Tiktok"}
},
"browser": "chrome",
"tz": "Europe/Paris",
"dateFormats": {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}
}
```

For each account, choose which steps to do :<br />
Step 1 (stepGetFollows) : get followers or following list and save it to a json file<br />
Step 2 (stepGetFollowsDetails) : get info of each follow and add them to Step 1 json file<br />
Step 3 (stepConvertJsonToExcel) : transform json file from step2 to a Excel file.<br /><br />
By setting triesStepGetFollowsDetails, you can do Step 2 several times to try again profiles you couldn't grab.<br />
If you cancel Step 2 before end of program execution, json file edits done by Step 2 won't be lost. So to continue without starting over, you can disable Step 1.

Run get-follows-details.py, it will create three files by account : one log, one json and one Excel file.

# Results
Fields : lineNumber	uniqueId	id	createTime	nickname	language	region (not available for months)	diggCount	videoCount	followerCount	followingCount	friendCount	privateAccount	bio	statusCode	statusMsg<br />
statusCode and statusMsg indicate if you could reach follow account.<br />

See sample files : dataset-tiktok-6863874874285622278_singularynapse.json and dataset-tiktok-6863874874285622278_singularynapse.xlsx<br />

![dataset-tiktok-6863874874285622278_singularynapse](https://github.com/user-attachments/assets/be0b8f13-392c-4dd9-a35c-e8123088221e)
