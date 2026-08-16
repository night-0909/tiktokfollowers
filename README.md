# Tiktok export followers and following list
Export Tiktok followers and following list to json file and Excel

getInfosAccounts.py : get id and creation date of Tiktok accounts<br/>
get-followers-details.py : export followers and following list of Tiktok accounts

For a list of Tiktok accounts, get their followers list (maximum : last 10000 followers) with their infos.<br />
Results are saved in a .json and .xlsx file.

**Usage :**<br /><br />
**1- Get numeric id of Tiktok account by running getInfosAccounts.py**<br />
First, for each Tiktok account you want their follower list, get their numeric id.<br />
Edit getInfosAccounts.py and input accounts name list at the end of script.<br />
Example : accounts = ["singularynapse"]<br />
Run getInfosAccounts.py and get : singularynapse : 6863874874285622278 created on 2021-07-29 20:03:48<br />
6863874874285622278 is numeric id of tiktok.com/@singularynapse account

**2- Export followers list of Tiktok accounts id by running get-followers-details.py**<br />
First, setup get-followers-details.settings.json with all accounts ids you want to export.<br />
Example : 
{"accounts": [
	{"id": "6863874874285622278", "steps": {"stepGetFollowers": true, "stepGetFollowersDetails": true, "stepConvertJsonToExcel": true}}<br />
],<br />
...<br />

For each account, choose which steps to do :<br />
Step 1 (stepGetFollowers) : get followers list and save it to a json file<br />
Step 2 (stepGetFollowersDetails) : get info of each followers and add them to Step 1 json file<br />
Step 3 (stepConvertJsonToExcel) : transform json file from step2 to a Excel file.<br /><br />
By setting triesStepGetFollowersDetails, you can do Step 2 several times to try again profiles you couldn't grab.<br />
If you cancel Step 2 before ending, json file edits done by Step 2 won't be lost. So to continue without starting over, you can disable Step 1 and enable only Step 2 and Step 3.

**Results :**<br /><br />
Fields : lineNumber	uniqueId	id	createTime	nickname	language	region (not available for months)	diggCount	videoCount	followerCount	followingCount	friendCount	privateAccount	bio	statusCode	statusMsg<br />
statusCode and statusMsg indicate if you could reach follower account.<br />

See sample files : dataset-tiktok-6863874874285622278_singularynapse.json and dataset-tiktok-6863874874285622278_singularynapse.xlsx<br />

![dataset-tiktok-6863874874285622278_singularynapse](https://github.com/user-attachments/assets/be0b8f13-392c-4dd9-a35c-e8123088221e)

As some accounts aren't accessible without being connected to Tiktok, you'll have better results if you have a Tiktok account.<br />
Connect to your Tiktok account and get your "sessionid_ss" and "tt-target-idc" cookies, then set them in get-followers-details.settings.json

**Following list :**<br /><br />
To get following list of a Tiktok account, you just need to change one value in get-followers-details.py.<br />
Change scene=67 by scene=21 at the top of getFollowers function :<br />
```python
response = curl_cffi.get( "https://www.tiktok.com/api/user/list/?count=30&maxCursor=0&minCursor=" + str(minCursor) + "&scene=67&secUid=" + account["secUid"], cookies=jsonSettings["httpRequest"]["cookies"], verify=jsonSettings["httpRequest"]["verifySSL"], impersonate=browser)
```
