# Tiktok export followers
Export Tiktok followers list to json file and Excel

getInfosAccounts.py : get id and creation date of Tiktok accounts<br/>
get-followers-details.py : export followers list of Tiktok accounts

For a list of Tiktok accounts, get their followers list (maximum : last 10000 followers) with their infos.<br />
Results are saved in a .json and .xlsx file.

**Input :**<br />
Setup get-followers-details.settings.json with all accounts you want to export.<br />
You need their id, get them with getInfosAccounts.py<br />
For each account, choose which step to do :<br />
Step 1 (stepGetFollowers) : get followers list and save it to a json file<br />
Step 2 (stepGetFollowersDetails) : get info of each followers and add them to Step 1 json file<br />
Step 3 (stepConvertJsonToExcel) : transform json file from step2 to a Excel file.<br /><br />
By setting triesStepGetFollowersDetails, you can do Step 2 several times to try again profiles you couldn't grab.<br />
If you cancel Step 2 before ending, json file edits done by Step 2 won't be lost. So to continue without starting over, you can disable Step 1 and enable only Step 2 and Step 3.

**Results :**<br />
Fields : lineNumber	uniqueId	id	createTime	nickname	language	region	diggCount	videoCount	followerCount	followingCount	friendCount	privateAccount	bio	statusCode	statusMsg<br />
statusCode and statusMsg indicate if you could reach follower account.<br />

See sample files : dataset-tiktok-6863874874285622278_singularynapse.json and dataset-tiktok-6863874874285622278_singularynapse.xlsx<br />

![dataset-tiktok-6863874874285622278_singularynapse](https://github.com/user-attachments/assets/be0b8f13-392c-4dd9-a35c-e8123088221e)

As some accounts aren't accessible without being connected to Tiktok, you'll have better results if you have a Tiktok account.

Connect to your Tiktok account and get your "sessionid_ss" and "tt-target-idc" cookies, then set them in get-followers-details.settings.json

