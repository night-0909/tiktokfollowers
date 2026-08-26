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
            logfile = "dataset-" + jsonSettings["scrape"] + "_" + account["id"] + ".log"
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
        log(account, f"[×] Error while requesting Tiktok for id {user_id} : {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    user_data_script = soup.select_one("script[id='__UNIVERSAL_DATA_FOR_REHYDRATION__']")
    
    return user_data_script

def getFollows(account):
    num_follows = 0

    if account["steps"]["stepGetFollows"] is True:
        followCount = "followerCount" if jsonSettings["scrape"] == 'followers' else "followingCount"
        
        log(account, "************ STEP GetFollows *************")
        log(account, "Get " + jsonSettings["scrape"] + " : " + str(account[followCount]))
        result = open(account["recordjson"], "w", encoding="utf-8")
        follows = []
        index = 1
        hasMore = True
        minCursor = 0
        line_number = 1
        while hasMore is True:
            try:
                scene = 67 if jsonSettings["scrape"] == 'followers' else 21
                response = curl_cffi.get(
                "https://www.tiktok.com/api/user/list/?count=30&maxCursor=0&minCursor=" + str(minCursor) +
                "&scene=" + str(scene) + "&secUid=" + account["secUid"], cookies=jsonSettings["httpRequest"]["cookies"],
                    verify=jsonSettings["httpRequest"]["verifySSL"], impersonate=browser)
                resjson = response.json()
                if response.status_code == 200:
                    followsjson = resjson.get("userList")

                    if followsjson is None:
                        log(account, "Error getting " + jsonSettings["scrape"] + " list, we skip this account")
                        return num_follows
                else:
                    log(account, f"[×] Response for https://www.tiktok.com/api/user/list/ isn't OK : status={response.status_code} text={response.text}")
                    return num_follows
            except Exception as e:
                log(account, f"[×] Error while requesting tiktok " + jsonSettings["scrape"] + " list for id {account['secUid']} : {e}")
                return num_follows

            # We only keep certain fields
            for follow in followsjson:
                # Sometimes Tiktok insert a dummy follow with empty values such as id: "0" and "uniqueId": ""
                # but with followerCount and followingCount set, so we d'ont keep it
                if follow.get("user")["id"] == "0":
                    log(account, "Dummy follow : " + str(follow))
                    continue

                user = {}
                user['lineNumber'] = line_number
                user["id"] = follow.get("user")["id"]
                user["uniqueId"] = follow.get("user")["uniqueId"]
                user["nickname"] = follow.get("user")["nickname"]
                user["diggCount"] = follow.get("stats")["diggCount"]
                user["videoCount"] = follow.get("stats")["videoCount"]
                user["followerCount"] = follow.get("stats")["followerCount"]
                user["followingCount"] = follow.get("stats")["followingCount"]
                user["privateAccount"] = "Yes" if follow.get("user")["privateAccount"] is True else "No"
                user["bio"] = follow.get("user")["signature"]
                follows.append(user)
                line_number = line_number + 1

            num_follows = len(follows)

            # Write followers/following to json file
            result.seek(0)
            result.write(json.dumps(follows))
            result.flush()
            log(account, jsonSettings["scrape"].capitalize() + " gathered : " + str(num_follows) + "/" + str(account[followCount]))

            minCursor = resjson["minCursor"]
            if resjson["hasMore"] is False:
                hasMore = False
            else:
                time.sleep(jsonSettings["delayCallGetFollows"])

            index = index + 1

        result.close()
        
        log(account, "Get " + jsonSettings["scrape"] + " done : " + str(num_follows))
    else:
        log(account, "We skip stepGetFollows")

    return num_follows

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

        # uniqueId and friendCount are problematic : uniqueId can be changed by the user and friendCount is always 0 in stepGetFollows
        user = user_info.get('user', {})
        stats = user_info.get('stats', {})
        create_time_unix = user.get('createTime', 0)
        create_time = datetime.fromtimestamp(create_time_unix, tzinfo).strftime(jsonSettings['dateFormats']['dateDBString']) if create_time_unix else 'N/A'

        userinfo["uniqueId"] = user.get('uniqueId')
        userinfo["secUid"] = user.get('secUid')
        # We get followerCount/followingCount here in order to print them for each account at the beginning of GetFollows Step
        userinfo["followerCount"] = stats.get("followerCount")
        userinfo["followingCount"] = stats.get("followingCount")
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
        log(account, "Try number " + str(resultStep["try"]) + " " + jsonSettings["scrape"] + " at the start : " + str(resultStep["num_follows_start"])
                 + " " + jsonSettings["scrape"] + " at the end : " + str(resultStep["num_follows_end"]) + " Errors : " + str(resultStep["errors"]))

def getFollowsDetails(account):
    # stepGetFollows : Get followers/following list with tiktok.com/api/user/list
    # additionnal infos : language, region, createTime and save it to JSON with key->value pair
    # We try jsonSettings["triesStepGetFollowsDetails"] times to get followers/following details
    if account["steps"]["stepGetFollowsDetails"] is True :
        log(account, "************ STEP GetFollowsDetails *************")
        tryindexStepGetFollowsDetails = 1
        resultsStep = []
        populateWithAdditionnalInfoCalls = 0

        if not os.path.isfile(account["recordjson"]):
            log(account, account["recordjson"] + " not found")
            return
        else:
            log(account, account["recordjson"] + " found")

        try:
            f = open(account["recordjson"], "r", encoding="utf-8")
            followsjson = json.load(f)
            num_follows_start = len(followsjson)
            f.close()
        except Exception as e:
            log(account, f"[×] Error with JSON file, either it's empty or json format is bad : {e}")
            return None

        while tryindexStepGetFollowsDetails < jsonSettings["triesStepGetFollowsDetails"] + 1:
            log(account, jsonSettings["scrape"].capitalize() + " : " + str(num_follows_start))
            log(account, "Try number " + str(tryindexStepGetFollowsDetails))
            new_follows = []
            index = 1
            errors = 0
            result = open(account["recordjson"], "w", encoding="utf-8")

            # We write in case no update is done and file could be empty until followsjson is scanned / So a program stoppage could end in a empty json
            result.seek(0)
            result.write(json.dumps(followsjson))
            result.flush()
            
            for follow in followsjson:
                # From api/user/list/, there's no createTime, language and region
                # In this step, if we can't find follower/following, createtime/language/region set with empty values => could be changed by not setting empty values in
                # populateWithAdditionnalInfo in block if user_data_script is None
                if "createTime" not in follow or follow["createTime"] == "":
                    follow = populateWithAdditionnalInfo(account=account, userinfo=follow, searchUserBy="id")
                    populateWithAdditionnalInfoCalls = populateWithAdditionnalInfoCalls + 1
                                            
                    # If we can't retrieve infos from follow homepage
                    if follow["createTime"] == "":
                        log(account, follow["id"] + "/" + follow["uniqueId"] + " unable to get additional data")
                        errors = errors + 1
                        if tryindexStepGetFollowsDetails == jsonSettings["triesStepGetFollowsDetails"]:
                            # We delete follow only if we are the last triesStepGetFollowsDetails
                            # del followsjson[index - 1]
                            log(account, follow["id"] + "/" + follow["uniqueId"] + " was never retrieved")

                        log(account, "Errors : " + str(errors))
                    else:
                        # We write the hole list after each follow is updated, in case of termination to not lose every account done
                        result.seek(0)
                        result.write(json.dumps(followsjson))
                        result.flush()

                    time.sleep(jsonSettings["delayCallGetFollowsDetails"])
               
                log(account, str(index) + "/" + str(num_follows_start))

                index = index + 1                
                if populateWithAdditionnalInfoCalls > 0 and populateWithAdditionnalInfoCalls == jsonSettings["WaitEveryXAccount"] and num_follows_start > 0:
                    log(account, "Every " + str(jsonSettings["WaitEveryXAccount"]) + " accounts, we wait " + str(jsonSettings["sleepEveryXAccount"]) + " seconds...")
                    time.sleep(jsonSettings["sleepEveryXAccount"])
                    populateWithAdditionnalInfoCalls = 0

            num_follows_end = len(followsjson)
            result.close()
            resultsStep.append({"try": tryindexStepGetFollowsDetails, "errors": errors, "num_follows_start": num_follows_start, "num_follows_end": num_follows_end})
            displayResultsStep(account, resultsStep)

            # OPTIONAL (use only if you uncomment this line above : # del followsjson[index - 1])
            # We recompute line numbers as we could have deleted some follows in this step
            #line_number = 1
            #result = open(account["recordjson"], "w", encoding="utf-8")
            #for follow in followsjson:
                #follow['lineNumber'] = line_number
                #line_number = line_number + 1

            #result.write(json.dumps(followsjson))
            #result.close()

            if errors > 0:            
                if tryindexStepGetFollowsDetails < jsonSettings["triesStepGetFollowsDetails"]:
                    log(account, "We wait " + str(jsonSettings["sleepAfterStepEnd"]) + " seconds before next try...")
                    time.sleep(jsonSettings["sleepAfterStepEnd"])

            tryindexStepGetFollowsDetails = tryindexStepGetFollowsDetails + 1
    else:
        log(account, "We skip stepGetFollowsDetails")

    # stepConvertJsonToExcel : Convert json file to final xlsx file
    if account["steps"]["stepConvertJsonToExcel"] is True:
        log(account, "************ STEP stepConvertJsonToExcel *************")

        if not os.path.isfile(account["recordjson"]):
            log(account, account["recordjson"] + " not found")
            return
        else:
            log(account, account["recordjson"] + " found")

        f = open(account["recordjson"], "r", encoding="utf-8")
        followsjson = json.load(f)
        f.close()

        # Write xlsx file
        writer = pd.ExcelWriter(account["recordexcel"], engine='xlsxwriter')
        df = pd.DataFrame({'lineNumber': [follower.get('lineNumber') for follower in followsjson],
                           'uniqueId': [follower.get('uniqueId') for follower in followsjson],
                           'id': [follower.get('id') for follower in followsjson],
                           'createTime': [follower.get('createTime') for follower in followsjson],
                           'nickname': [follower.get('nickname') for follower in followsjson],
                           'language': [follower.get('language') for follower in followsjson],
                           'region': [follower.get('region') for follower in followsjson],
                           'diggCount': [follower.get('diggCount') for follower in followsjson],
                           'videoCount': [follower.get('videoCount') for follower in followsjson],
                           'followerCount': [follower.get('followerCount') for follower in followsjson],
                           'followingCount': [follower.get('followingCount') for follower in followsjson],
                           'friendCount': [follower.get('friendCount') for follower in followsjson],
                           'privateAccount': [follower.get('privateAccount') for follower in followsjson],
                           'bio': [follower.get('bio') for follower in followsjson],
                           'statusCode': [follower.get('statusCode') for follower in followsjson],
                           'statusMsg': [follower.get('statusMsg') for follower in followsjson]
                           })

        df = df.T.reset_index().T
        df.to_excel(writer, sheet_name=jsonSettings["scrape"], header=None, index=False)
        writer.sheets[jsonSettings["scrape"]].autofit()
        writer.close()
    else:
        log(account, "We skip stepConvertJsonToExcel")
        
    # Close log file for this account
    log(account, "DONE")
    account["recordlog"].close()

if __name__ == "__main__":
    fprogram = open("get-follows-details.log", "a", encoding="utf-8")

    # Get vars from json settings file
    jsonSettingsFile = "get-follows-details.settings.json"
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
            account["recordjson"] = "dataset-tiktok-" + jsonSettings["scrape"] + "-" + account["id"] + "_" + account["uniqueId"] + ".json"
            account["recordexcel"] = "dataset-tiktok-" + jsonSettings["scrape"] + "-" + account["id"] + "_" + account["uniqueId"] + ".xlsx"
            logfile = "dataset-tiktok-" + jsonSettings["scrape"] + "-" + account["id"] + "_" + account["uniqueId"] + ".log"
            logfileH = open(logfile, "a", encoding="utf-8")
            account["recordlog"] = logfileH

            # Log debug info
            log(account, account["recordjson"])
            log(account, account["recordexcel"])
            time.sleep(jsonSettings["delayCallGetFollows"])
        else:
            log(account, "Unable to gather account info in the initialization step")

    # Get followers/following list
    for index, account in enumerate(jsonSettings["accounts"]):
        num_follows = getFollows(account)
        if (num_follows) > 0 and index < len(jsonSettings["accounts"]) - 1:
            log(account, "Before next account, we wait " + str(jsonSettings["sleepAfterNextAccount"]) + " seconds...")
            time.sleep(jsonSettings["sleepAfterNextAccount"])

    # Get additionnal infos for followers/following
    threads = []
    for account in jsonSettings["accounts"]:
        threadGetFollowsDetails = threading.Thread(target=getFollowsDetails, args=(account,))
        threads.append(threadGetFollowsDetails)
        threadGetFollowsDetails.start()

    for thread in threads:
        thread.join()

    log(None, "Program ended")
    fprogram.close()
