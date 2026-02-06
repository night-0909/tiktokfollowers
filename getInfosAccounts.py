import requests, curl_cffi
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import time

def get_user_data_script(user_id):
    user_data_script = None
    
    try:
        response = curl_cffi.get(f'https://www.tiktok.com/@{user_id}', cookies=cookies,
                                 verify=True, impersonate=browser)
        
        if response.status_code != 200:
            print(f"[×] Response for https://www.tiktok.com/@{user_id} isn't OK : status={response.status_code} text={response.text}")
            return None
    except Exception as e:
        print(f"[×] Error while requesting tiktok for id {user_id} : {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    user_data_script = soup.select_one("script[id='__UNIVERSAL_DATA_FOR_REHYDRATION__']")
    
    return user_data_script

def get_info(username):
    userinfoResult = None

    user_data_script = get_user_data_script(username)
    if user_data_script is not None:
        try:
            user_data_json = json.loads(user_data_script.text)
            webappuserdetail = user_data_json.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {})

            userinfoResult = {}
            userinfoResult["statusCode"] = webappuserdetail.get('statusCode')
            userinfoResult["statusMsg"] = webappuserdetail.get('statusMsg')
            
            if userinfoResult["statusCode"] != 0:
                print(f"[×] Profile {username} isn't accessible statusCode={userinfoResult['statusCode']} statusMsg={userinfoResult['statusMsg']}")
            else:
                user_info = webappuserdetail.get('userInfo', {})
                user = user_info.get('user', {})
                userinfoResult["id"] = user.get('id')
                
                create_time_unix = user.get('createTime', 0)
                create_time = datetime.fromtimestamp(create_time_unix, tzinfo).strftime(dateFormat) if create_time_unix else 'N/A'
                userinfoResult["createTime"] = create_time
                    
        except json.JSONDecodeError as e:
            print(f"[×] JSON decoding error: {e}")
        except Exception as e:
            print(f"[×] Error while processing data: {e}")

    return userinfoResult

accounts = [""]
cookies = {"sessionid_ss": "", "tt-target-idc": "eu-ttp2"}
browser = 'chrome'
tzinfo = ZoneInfo("Europe/Paris")
dateFormat = '%Y-%m-%d %H:%M:%S'

for account in accounts:
    user = get_info(account)
    if user is not None:
        if user["statusCode"] == 0:
            print(account + " : " + str(user["id"]) + " created on " + str(user["createTime"]))        
    else:
        print(account + " : error.")
        
    time.sleep(2)

