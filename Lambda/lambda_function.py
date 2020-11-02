import os, re, json, logging, datetime
import urllib.request
from urllib.parse import parse_qs

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handle_slack_event(slack_event: dict, context) -> str:
    # 受け取ったイベント情報をCloud Watchログに出力
    logging.info(json.dumps(slack_event))

    body = parse_qs(slack_event.get('body') or '') #ペイロードのbody取得
    json_open = body['payload'][0]
    json_load = json.loads(json_open)
    interactiveType = json_load["container"]["type"]

    print(json_load)

    if interactiveType == "view":   # HomeTabからのペイロード
        # Kent, Saeko, Ayaka, Minami, Nanae, Nanako, Rina, Henri, Kugi, Masato, Yoshi, Ayumu, Oki, Osa, Sanpei
        # userIDs = ["U018DM5NAQ4", "UE32RF9SB", "U0119D0703S", "UU2S7SHSL", "UH8AZEFCJ", "UG4AGRPEW", "UV5J27J8Z", "UD452K55H", "UKRTDTU6P", "UCRU2CRKP", "UCR1Y87KJ", "U010M6ETTGU", "UCS8B84JV", "UDBFZTFN0", "UD41MDCVA"]
        # userIDs = ["U018DM5NAQ4", "UE32RF9SB"] # テスト用ユーザー
        userIDs = ["U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4"] # 大量投稿テスト用ユーザー
        yesNo = json_load['actions'][0]['value']

        # 値判定でメッセージ切り替え
        if yesNo == "yes":
            with open('MealsYes_Staff_201023.json') as f:
                data = f.read()
            message = data

            # userJson = channelMemberGet()  # mealsチャンネルのユーザー取得
            # json_perse = json.load(userJson)
            # for im in json_perse["members"]:
            #     userIDs.append(im)

            for userID in userIDs:
                post_message_to_slack(message, userID, "attachments")

        elif yesNo == "no":
            with open('MealsNo_Staff.json') as f:
                data = f.read()
            message = data
            post_message_to_slack(message, "python-test", "attachments")
        else:
            with open('MealsNo_Staff.json') as f:
                data = f.read()
            message = data
            post_message_to_slack(message, "python-test", "attachments")

    elif interactiveType == "message_attachment": # channelからのペイロード
        username = json_load["user"]["username"]
        jsonDict = json_load["state"]["values"]
        jsonDecision = json_load["actions"][0]["action_id"]

        jsonList = list(jsonDict.values())
        try:
            guest = jsonList[1]["actionId-3"]["selected_option"]["value"]
        except:
            guest = "0"

        try:
            genre = jsonList[2]["actionId-4"]["selected_option"]["value"]
        except:
            genre = "なんでもいいよ！"

        message =  username + "/" + guest + "/" + genre

        if jsonDecision == "action_id-select":
            responseURL = json_load["response_url"]
            print(responseURL)
            responseButton(responseURL)

            post_message_to_slack(message, "U018DM5NAQ4", "text") # Kent
            post_message_to_slack(message, "UE32RF9SB", "text") # Saeko

    else:   # 例外処理
        with open('MealsNo_Staff.json') as f:
            data = f.read()
            message = data
        post_message_to_slack(message, "python-test", "attachments")

    # メッセージの投稿とは別に、Event APIによるリクエストの結果として
    # Slackに何かしらのレスポンスを返す必要があるのでOKと返す
    # （返さない場合、失敗とみなされて同じリクエストが何度か送られてくる）
    return "OK"


def post_message_to_slack(message: str, channel: str, kind: str):
    # Slackのchat.postMessage APIを利用して投稿する
    # ヘッダーにはコンテンツタイプとボット認証トークンを付与する
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }

    if kind == "attachments": # Homeタブからの情報
        date1 = datetime.date.today()
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": "*" + str(date1) + "*",
            "attachments": message,
            "username": "Bot-Sample"
        }
    elif kind == 'text': # Channelからの命令
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": message,
            "username": "Bot-Sample"
        }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers)
    urllib.request.urlopen(req)

    return

def channelMemberGet(): # 今は未使用（チャンネルが見つからないと言われる）
    url = "https://slack.com/api/conversations.members"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }
    data = {
        "token": os.environ["SLACK_APP_AUTH_TOKEN"],
        "channel": "U01CCS31N2F"
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="GET", headers=headers)
    userJson = urllib.request.urlopen(req)

    return userJson


def responseButton(url: str):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }
    data = {
        "token": os.environ["SLACK_APP_AUTH_TOKEN"],
        "text": "OK:ok_hand:"
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers)
    urllib.request.urlopen(req)

    return
