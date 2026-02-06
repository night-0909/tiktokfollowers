# tiktok
Export Tiktok followers list to Excel

getInfosAccounts.py : get id and creation date of Tiktok accounts<br/>
get-followers-details.py : export followers list of Tiktok accounts

For a list of Tiktok accounts, get their followers list (maximum : last 10000 followers) with their infos.<br />
Results are in a .json file and .xlsx file

Input :<br />
Setup get-followers-details.settings.json with all accounts you want to export.
You need their id, get them with getInfosAccounts.py

You'll have better results if you have a Tiktok account : connect to Tiktok et get your "sessionid_ss" cookie, then set it in get-followers-details.settings.json
