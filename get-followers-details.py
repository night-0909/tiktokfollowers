# -*- encoding: utf-8 -*-

# Need to impersonate browser to call tiktok.com
# impersonate browser : https://scrapfly.io/blog/curl-impersonate-scrape-chrome-firefox-tls-http2-fingerprint/
# https://brightdata.com/blog/web-data/web-scraping-with-curl-cffi

import requests
import curl_cffi
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import threading
import os, sys, time

def log(account, message):
    date = datetime.fromtimestamp(datetime.now().timestamp(), tzinfo)
    strBeforeMessage = date.strftime(jsonSettings['dateFormats']['dateString'])

    if account is not None:
        # uniqueId can be None when a call to Tiktok gets wrong
        if "uniqueId" not in account:
            account["uniqueId"] = ""

        strBeforeMessage = strBeforeMessage + " Account id " + account["id"] + " / uniqueId " + account["uniqueId"]

    print(strBeforeMessage + " " + message)

    # We log in accountXX.log
    if account is not None:
        # "recordlog" can be unset at the step where we gather uniqueId of accounts, so we set log filename without uniqueId
        if "recordlog" not in account:
            logfile = "dataset-" + account["id"] + ".log"
            logfileH = open(logfile, "a", encoding="utf-8")
            account["recordlog"] = logfileH

        account["recordlog"].write(strBeforeMessage + " " + message + "\n")
        account["recordlog"].flush()
    else:
        # We log in program.log
        fprogram.write(strBeforeMessage + " " + message + "\n")
        fprogram.flush()

def get_user_data_script(account, userinfo):
    user_data_script = None
    user_id = userinfo["id"]
    
    try:
        # jsonSettings["httpRequest"]["cookies"] is useful to grab some profiles where login is necessary
        response = curl_cffi.get(f'https://www.tiktok.com/@{user_id}', cookies=jsonSettings["httpRequest"]["cookies"],
                                 verify=jsonSettings["httpRequest"]["verifySSL"], impersonate=browser)
        
        if response.status_code != 200:
            log(account, f"[×] Response for https://www.tiktok.com/@{user_id} isn't OK : status={response.status_code} text={response.text}")
            return None
    except Exception as e:
        log(account, f"[×] Error while requesting tiktok for id {user_id} : {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    user_data_script = soup.select_one("script[id='__UNIVERSAL_DATA_FOR_REHYDRATION__']")
    
    return user_data_script

def getFollowers(account):
    num_followers = 0

    if account["steps"]["stepGetFollowers"] is True:
        log(account, "************ STEP GetFollowers *************")
        log(account, "Get followers : " + str(account["followerCount"]))
        result = open(account["recordjson"], "w", encoding="utf-8")
        followers = []
        index = 1
        hasMore = True
        minCursor = 0
        line_number = 1
        while hasMore is True:
            try:
                response = curl_cffi.get(
                "https://www.tiktok.com/api/user/list/?count=30&maxCursor=0&minCursor=" + str(minCursor) +
                "&scene=67&secUid=" + account["secUid"], cookies=jsonSettings["httpRequest"]["cookies"],
                    verify=jsonSettings["httpRequest"]["verifySSL"], impersonate=browser)
                resjson = response.json()
                if response.status_code == 200:
                    followersjson = resjson.get("userList")

                    if followersjson is None:
                        log(account, "Error getting followers list, we skip this account")
                        return num_followers
                else:
                    log(account, f"[×] Response for https://www.tiktok.com/api/user/list/ isn't OK : status={response.status_code} text={response.text}")
                    return num_followers
            except Exception as e:
                log(account, f"[×] Error while requesting tiktok follower list for id {account['secUid']} : {e}")
                return num_followers
            
            num_followers = len(followersjson)

            # We keep only certain fields
            for follower in followersjson:
                user = {}
                user['lineNumber'] = line_number
                user["id"] = follower.get("user")["id"]
                user["uniqueId"] = follower.get("user")["uniqueId"]
                user["nickname"] = follower.get("user")["nickname"]
                user["diggCount"] = follower.get("stats")["diggCount"]
                user["videoCount"] = follower.get("stats")["videoCount"]
                user["followerCount"] = follower.get("stats")["followerCount"]
                user["followingCount"] = follower.get("stats")["followingCount"]
                user["privateAccount"] = "Yes" if follower.get("user")["privateAccount"] is True else "No"
                user["bio"] = follower.get("user")["signature"]
                followers.append(user)
                line_number = line_number + 1

            # Write followers to json file
            result.seek(0)
            result.write(json.dumps(followers))
            result.flush()
            log(account, "Followers gathered : " + str(len(followers)) +"/" + str(account["followerCount"]))

            minCursor = resjson["minCursor"]
            if resjson["hasMore"] is False:
                hasMore = False
            else:
                time.sleep(jsonSettings["delayCallGetFollowers"])

            index = index + 1

        result.close()
        log(account, "Get followers done : " + str(len(followers)))
    else:
        log(account, "We skip stepGetFollowers")

    return num_followers

def populateWithAdditionnalInfo(*, account, userinfo, searchUserBy="id"):
    user_data_script = get_user_data_script(account, userinfo)
    userSearchField = userinfo[searchUserBy]

    if user_data_script is None:
        userinfo["createTime"] = ""
        userinfo["language"] = ""
        userinfo["region"] = "" # region doesn't seem to be returned by Tiktok anymore
        # Define a nonexistent Tiktok statusCode and statusMsg for this case
        userinfo["statusCode"] = 99999
        userinfo["statusMsg"] = "Error getting Tiktok page"
        return userinfo
    try:
        user_data_json = json.loads(user_data_script.text)

        # First, check if profile is accessible looking at statusCode (0 = OK)
        # List of statusCode and statusMessage and their meaning : see https://github.com/davidteather/TikTok-Api/issues/403#issuecomment-971818109
        webappuserdetail = user_data_json.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})
        userinfo["statusCode"] = webappuserdetail.get('statusCode')
        userinfo["statusMsg"] = webappuserdetail.get('statusMsg')

        # Error while getting profile, possible causes : TK profile don't exist anymore or it isn't accessible (need to login, private,
        # audience control is activated by owner, sensitive content, or other reasons see statusMsg)
        if userinfo["statusCode"] != 0:
            userinfo["createTime"] = ""
            userinfo["language"] = ""
            userinfo["region"] = ""
            log(account, f"[×] Profile isn't accessible statusCode={userinfo['statusCode']} statusMsg={userinfo['statusMsg']}")
            return userinfo
        
        # Profile is accessible        
        user_info = webappuserdetail.get('userInfo', {})

        # uniqueId and friendCount are problematic : uniqueId can be changed by the user and friendCount is always 0 in stepGetFollowers
        user = user_info.get('user', {})
        stats = user_info.get('stats', {})
        create_time_unix = user.get('createTime', 0)
        create_time = datetime.fromtimestamp(create_time_unix, tzinfo).strftime(jsonSettings['dateFormats']['dateDBString']) if create_time_unix else 'N/A'

        userinfo["uniqueId"] = user.get('uniqueId')
        userinfo["secUid"] = user.get('secUid')
        # We get followerCount here in order to print followersCount for each accounts at the beginning of GetFollowers Step
        userinfo["followerCount"] = stats.get("followerCount")
        userinfo["createTime"] = create_time
        userinfo["language"] = user.get('language')
        userinfo["region"] = user.get('region')

        stats = user_info.get('stats', {})
        userinfo["friendCount"] = stats["friendCount"]
        
    except json.JSONDecodeError as e:
        log(account, f"[×] JSON decoding error for {searchUserBy} {userSearchField} : {e}")
        return None
    except Exception as e:
        log(account, f"[×] Error while processing data for {searchUserBy} {userSearchField} : {e}")
        return None

    return userinfo

def displayResultsStep(account, resultsStep):
    for resultStep in resultsStep:
        log(account, "Try number " + str(resultStep["try"]) + "  Followers at the start : " + str(resultStep["num_followers_start"])
                 + "  Followers at the end : " + str(resultStep["num_followers_end"]) + " Errors : " + str(resultStep["errors"]))

def getFollowersDetails(account):
    # stepGetFollowers : Get followers list with tiktok.com/api/user/list
    # additionnal infos : language, region, createTime and save it to JSON with key->value pair
    # We try jsonSettings["triesStepGetFollowersDetails"] times to get followers details
    if account["steps"]["stepGetFollowersDetails"] is True :
        log(account, "************ STEP GetFollowersDetails *************")
        tryindexStepGetFollowersDetails = 1
        resultsStep = []
        populateWithAdditionnalInfoCalls = 0

        if not os.path.isfile(account["recordjson"]):
            log(account, account["recordjson"] + " not found")
            return
        else:
            log(account, account["recordjson"] + " found")

        try:
            f = open(account["recordjson"], "r", encoding="utf-8")
            followersjson = json.load(f)
            num_followers_start = len(followersjson)
            f.close()
        except Exception as e:
            log(account, f"[×] Error with JSON file, either it's empty or json format is bad : {e}")
            return None

        while tryindexStepGetFollowersDetails < jsonSettings["triesStepGetFollowersDetails"] + 1:
            log(account, "Followers : " + str(num_followers_start))
            log(account, "Try number " + str(tryindexStepGetFollowersDetails))
            new_followers = []
            index = 1
            errors = 0
            result = open(account["recordjson"], "w", encoding="utf-8")

            # We write in case no update is done and file could be empty until followersjson is scanned / So a program stoppage could end in a empty json
            result.seek(0)
            result.write(json.dumps(followersjson))
            result.flush()
            
            for follower in followersjson:
                # From api/user/list/, there's no createTime, language and region
                # In this step, if we can't find follower, createtime/language/region set with empty values => could be changed by not setting empty values in
                # populateWithAdditionnalInfo in block if user_data_script is None
                if "createTime" not in follower or follower["createTime"] == "":
                    follower = populateWithAdditionnalInfo(account=account, userinfo=follower, searchUserBy="id")
                    populateWithAdditionnalInfoCalls = populateWithAdditionnalInfoCalls + 1
                                            
                    # If we can't retrieve infos from follower homepage
                    if follower["createTime"] == "":
                        log(account, follower["id"] + "/" + follower["uniqueId"] + " unable to get additional data")
                        errors = errors + 1
                        if tryindexStepGetFollowersDetails == jsonSettings["triesStepGetFollowersDetails"]:
                            # We delete follower only if we are the last triesStepGetFollowersDetails
                            # del followersjson[index - 1]
                            log(account, follower["id"] + "/" + follower["uniqueId"] + " was never retrieved")

                        log(account, "Errors : " + str(errors))
                    else:
                        # We write the hole list after each follower is updated, in case of termination to not lose every account done
                        result.seek(0)
                        result.write(json.dumps(followersjson))
                        result.flush()

                    time.sleep(jsonSettings["delayCallGetFollowersDetails"])
               
                log(account, str(index) + "/" + str(num_followers_start))

                index = index + 1                
                if populateWithAdditionnalInfoCalls > 0 and populateWithAdditionnalInfoCalls == jsonSettings["WaitEveryXAccount"] and num_followers_start > 0:
                    log(account, "Every " + str(jsonSettings["WaitEveryXAccount"]) + " accounts, we wait " + str(jsonSettings["sleepEveryXAccount"]) + " seconds...")
                    time.sleep(jsonSettings["sleepEveryXAccount"])
                    populateWithAdditionnalInfoCalls = 0

            num_followers_end = len(followersjson)
            result.close()
            resultsStep.append({"try": tryindexStepGetFollowersDetails, "errors": errors, "num_followers_start": num_followers_start, "num_followers_end": num_followers_end})
            displayResultsStep(account, resultsStep)

            # OPTIONAL (use only if you uncomment this line above : # del followersjson[index - 1])
            # We recompute line numbers as we could have deleted some followers in this step
            line_number = 1
            result = open(account["recordjson"], "w", encoding="utf-8")
            for follower in followersjson:
                follower['lineNumber'] = line_number
                line_number = line_number + 1

            result.write(json.dumps(followersjson))
            result.close()

            if errors > 0:            
                if tryindexStepGetFollowersDetails < jsonSettings["triesStepGetFollowersDetails"]:
                    log(account, "We wait " + str(jsonSettings["sleepAfterStepEnd"]) + " seconds before next try...")
                    time.sleep(jsonSettings["sleepAfterStepEnd"])

            tryindexStepGetFollowersDetails = tryindexStepGetFollowersDetails + 1
    else:
        log(account, "We skip stepGetFollowersDetails")

    # stepConvertJsonToExcel : Convert json file to final xlsx file
    if account["steps"]["stepConvertJsonToExcel"] is True:
        log(account, "************ STEP stepConvertJsonToExcel *************")

        if not os.path.isfile(account["recordjson"]):
            log(account, account["recordjson"] + " not found")
            return
        else:
            log(account, account["recordjson"] + " found")

        f = open(account["recordjson"], "r", encoding="utf-8")
        followersjson = json.load(f)
        f.close()

        # Write xlsx file
        writer = pd.ExcelWriter(account["recordexcel"], engine='xlsxwriter')
        df = pd.DataFrame({'lineNumber': [follower.get('lineNumber') for follower in followersjson],
                           'uniqueId': [follower.get('uniqueId') for follower in followersjson],
                           'id': [follower.get('id') for follower in followersjson],
                           'createTime': [follower.get('createTime') for follower in followersjson],
                           'nickname': [follower.get('nickname') for follower in followersjson],
                           'language': [follower.get('language') for follower in followersjson],
                           'region': [follower.get('region') for follower in followersjson],
                           'diggCount': [follower.get('diggCount') for follower in followersjson],
                           'videoCount': [follower.get('videoCount') for follower in followersjson],
                           'followerCount': [follower.get('followerCount') for follower in followersjson],
                           'followingCount': [follower.get('followingCount') for follower in followersjson],
                           'friendCount': [follower.get('friendCount') for follower in followersjson],
                           'privateAccount': [follower.get('privateAccount') for follower in followersjson],
                           'bio': [follower.get('bio') for follower in followersjson],
                           'statusCode': [follower.get('statusCode') for follower in followersjson],
                           'statusMsg': [follower.get('statusMsg') for follower in followersjson]
                           })

        df = df.T.reset_index().T
        df.to_excel(writer, sheet_name='Followers', header=None, index=False)
        writer.sheets["Followers"].autofit()
        writer.close()
    else:
        log(account, "We skip stepConvertJsonToExcel")
        
    # Close log file for this account
    log(account, "DONE")
    account["recordlog"].close()

if __name__ == "__main__":
    fprogram = open("get-followers-details.log", "a", encoding="utf-8")

    # Get vars from json settings file
    jsonSettingsFile = "get-followers-details.settings.json"
    f = open(jsonSettingsFile, "r", encoding="utf-8")
    jsonSettings = json.load(f)
    f.close()

    tzinfo = ZoneInfo(jsonSettings["tz"])
    browser = jsonSettings["browser"]

    # ************** Launch program **************
    log(None, "Program started")

    # Populate filenames and set log file handle in jsonSettings["accounts"] array
    for index, account in enumerate(jsonSettings["accounts"]):
        account = populateWithAdditionnalInfo(account=account, userinfo=account, searchUserBy="id")
        if (account["createTime"] != ""):
            account["recordjson"] = "dataset-tiktok-" + account["id"] + "_" + account["uniqueId"] + ".json"
            account["recordexcel"] = "dataset-tiktok-" + account["id"] + "_" + account["uniqueId"] + ".xlsx"
            logfile = "dataset-tiktok-" + account["id"] + "_" + account["uniqueId"] + ".log"
            logfileH = open(logfile, "a", encoding="utf-8")
            account["recordlog"] = logfileH

            # Log debug info
            log(account, account["recordjson"])
            log(account, account["recordexcel"])
            time.sleep(jsonSettings["delayCallGetFollowers"])
        else:
            log(account, "Unable to gather account info in the initialization step")

    # Get followers list
    for index, account in enumerate(jsonSettings["accounts"]):
        num_followers = getFollowers(account)
        if (num_followers) > 0 and index < len(jsonSettings["accounts"]) - 1:
            log(account, "Before next account, we wait " + str(jsonSettings["sleepAfterNextAccount"]) + " seconds...")
            time.sleep(jsonSettings["sleepAfterNextAccount"])

    # Get additionnal infos for followers
    threads = []
    for account in jsonSettings["accounts"]:
        threadGetFollowersDetails = threading.Thread(target=getFollowersDetails, args=(account,))
        threads.append(threadGetFollowersDetails)
        threadGetFollowersDetails.start()

    for thread in threads:
        thread.join()

    log(None, "Program ended")
    fprogram.close()
