import os
import re
import json
import logging
import datetime
import boto3
import urllib.request
from urllib.parse import parse_qs

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_slack_event(slack_event: dict, context) -> str:
    # 受け取ったイベント情報をCloud Watchログに出力
    logging.info(json.dumps(slack_event))
    body = parse_qs(slack_event["event"].get('body') or '')  # ペイロードのbody取得
    json_open = body['payload'][0]
    json_load = json.loads(json_open)

    interactiveType = json_load["container"]["type"]
    yesNo = json_load['actions'][0]['value']

    if interactiveType == "view":   # HomeTabからのペイロード
        # Kent, Ayaka, Minami, Nanae, Nanako, Rina, Henri, Kugi, Masato, Yoshi, Ayumu, Oki, Osa, Sanpei, Saeko
        # userIDs = ["U018DM5NAQ4", "U0119D0703S", "UU2S7SHSL", "UH8AZEFCJ", "UG4AGRPEW", "UV5J27J8Z", "UD452K55H", "UKRTDTU6P", "UCRU2CRKP", "UCR1Y87KJ", "U010M6ETTGU", "UCS8B84JV", "UDBFZTFN0", "UD41MDCVA", "UE32RF9SB"] # 本番用
        # userIDs = ["U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB","U018DM5NAQ4", "UE32RF9SB", "U018DM5NAQ4"] # 管理者大量投稿テスト用
        # userIDs = ["U018DM5NAQ4", "UE32RF9SB"] # 管理者テスト用
        userIDs = ["U018DM5NAQ4"]  # 管理者テスト用

        # 値判定でメッセージ切り替え
        # Mealsあり
        if yesNo == "yes40" or yesNo == "yes30" or yesNo == "yes20" or yesNo == "yes10":
            with open('YesMeals.json') as f:
                data = f.read()
            message = data

            for userID in userIDs:
                post_message_to_slack(message, userID, "attachments", yesNo)

        elif yesNo == "no":  # Mealsなし
            with open('NoMeals.json') as f:
                data = f.read()
            message = data

            for userID in userIDs:
                post_message_to_slack(
                    message, userID, "attachmentsAndNo", yesNo)

        elif yesNo == "total":  # 集計結果表示
            # S3の設定
            S3_BUCKET_NAME = "lambda-meals"
            S3_DB_NAME = "Syukei.json"
            S3_client = boto3.client('s3')

            # DBから情報取得(集計)
            response = S3_client.get_object(
                Bucket=S3_BUCKET_NAME, Key=S3_DB_NAME)
            data = json.loads(response["Body"].read())

            message = aggregate(data)
            cleanJson = json_0(data)

            for userID in userIDs:
                post_message_to_slack(message, userID, "aggregate", yesNo)

            S3_client.put_object(Body=json.dumps(
                data, indent=4), Bucket=S3_BUCKET_NAME, Key=S3_DB_NAME)

        else:
            with open('NoMeals.json') as f:
                data = f.read()
            message = data

            for userID in userIDs:
                post_message_to_slack(
                    message, userID, "attachmentsAndNo", yesNo)

    elif interactiveType == "message_attachment":  # channelからのペイロード
        username = json_load["user"]["username"]
        jsonDict = json_load["state"]["values"]
        jsonDecision = json_load["actions"][0]["action_id"]

        # forを使うのは、jsonの中身がいつも違う順番で来る為
        jsonList = list(jsonDict.values())
        for i in [0, 1, 2, 3]:  # ゲストの数
            try:
                guest = jsonList[i]["actionId-3"]["selected_option"]["value"]
                break
            except:
                guest = "0"
        for j in [0, 1, 2, 3]:  # 希望ジャンル
            try:
                genre = jsonList[j]["actionId-4"]["selected_option"]["value"]
                break
            except:
                genre = "allok"
        for k in [0, 1, 2, 3]:  # yesかどうか
            try:
                staffs = jsonList[k]["actionId-yesno"]["selected_option"]["value"]
                break
            except:
                staffs = "0"

        # DB更新
        # S3の設定
        S3_BUCKET_NAME = "lambda-meals"
        S3_DB_NAME = "Syukei.json"
        S3_client = boto3.client('s3')

        # DBから情報取得(更新の為)
        response = S3_client.get_object(Bucket=S3_BUCKET_NAME, Key=S3_DB_NAME)
        data = json.loads(response["Body"].read())
        data[genre] = add_genre(data, genre)
        data["guest"] = if_add_guest(data, guest)
        data["ormore"] = if_add_5moreguest(data, guest)
        data["staff"] = if_add_a_staff(data, staffs)

        staffNum = if_staffname_in(data, username)
        if staffNum == 1000:
            data["name_error"] = data["name_error"] + 1
        else:
            data[staffNum] = 1

        guestNum = if_guest_in(guest)
        userGuest = if_userGuest_in(username)
        data[userGuest] = data[userGuest] + guestNum

        S3_client.put_object(Body=json.dumps(data, indent=4),
                             Bucket=S3_BUCKET_NAME, Key=S3_DB_NAME)

        message = username + "/" + guest + "/" + genre

        if jsonDecision == "action_id-select":
            responseURL = json_load["response_url"]
            responseButton(responseURL)

            post_message_to_slack(message, "U018DM5NAQ4",
                                  "text", yesNo)  # Kent
            # post_message_to_slack(message, "UE32RF9SB", "text", yesNo) # Saeko

    else:   # 例外処理
        with open('NoMeals.json') as f:
            data = f.read()
            message = data
        post_message_to_slack(message, "UE32RF9SB", "attachmentsAndNo", yesNo)

    # メッセージの投稿とは別に、Event APIによるリクエストの結果として
    # Slackに何かしらのレスポンスを返す必要があるのでOKと返す
    # （返さない場合、失敗とみなされて同じリクエストが何度か送られてくる）
    return "OK"

# Slackへの投稿


def post_message_to_slack(message: str, channel: str, kind: str, min: str):
    # Slackのchat.postMessage APIを利用して投稿する
    # ヘッダーにはコンテンツタイプとボット認証トークンを付与する
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }

    if kind == "attachments":  # Homeタブから全員へ
        date = datetime.date.today()
        deadline = getDeadline(min)
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": "*" + str(date) + "*\n必要な方は" + str(deadline) + "までにお知らせください" + " :rice_ball:",
            "attachments": message,
            "username": "Bot-Sample"
        }
    elif kind == 'text':  # Channelから管理者へ
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": message,
            "username": "Bot-Sample"
        }
    elif kind == "attachmentsAndNo":
        date = datetime.date.today()
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": "*" + str(date) + "*",
            "attachments": message,
            "username": "Bot-Sample"
        }
    elif kind == "aggregate":
        data = {
            "token": os.environ["SLACK_APP_AUTH_TOKEN"],
            "channel": "@" + channel,
            "text": "*集計結果*\n" + message,
            "username": "Bot-Sample"
        }

    req = urllib.request.Request(url, data=json.dumps(
        data).encode("utf-8"), method="POST", headers=headers)
    urllib.request.urlopen(req)

    return

# Staffのアクションに対してメッセージを書き換え


def responseButton(url: str):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }
    data = {
        "token": os.environ["SLACK_APP_AUTH_TOKEN"],
        "text": "OK:ok_hand:"
    }

    req = urllib.request.Request(url, data=json.dumps(
        data).encode("utf-8"), method="POST", headers=headers)
    urllib.request.urlopen(req)

    return

# 締め切りの時間取得


def getDeadline(min):
    if min == "yes40":
        td_m = datetime.timedelta(minutes=580)
    elif min == "yes30":
        td_m = datetime.timedelta(minutes=570)
    elif min == "yes20":
        td_m = datetime.timedelta(minutes=560)
    elif min == "yes10":
        td_m = datetime.timedelta(minutes=550)
    else:
        td_m = datetime.timedelta()

    dt_now = datetime.datetime.now()
    dt_m = dt_now + td_m

    return dt_m.strftime('%H:%M')

# 各ジャンルのカウント追加


def add_genre(fJson, type):
    return fJson[type] + 1

# ゲスト数追加


def if_add_guest(fJson, s):
    if '1' in s:
        guest_test = 1
    elif '2' in s:
        guest_test = 2
    elif '3' in s:
        guest_test = 3
    elif '4' in s:
        guest_test = 4
    else:
        guest_test = 0  # 5人以上のときも０にしている

    return fJson["guest"] + guest_test


# ゲスト5人以上の時の追加
def if_add_5moreguest(fJson, d):
    if '5' in d:
        guest_test_5more = 5
    else:
        guest_test_5more = 0

    return fJson["ormore"] + guest_test_5more


# 必要スタッフ数のカウント追加
def if_add_a_staff(fJson, s):
    if s == 'yes':
        staff_number = 1

    return fJson["staff"] + staff_number


# 各スタッフを1にする
def if_staffname_in(fJson, s):
    try:
        if 'ayaka' in s:
            username_emoji = "ayaka"
        elif 'ayumu' in s:
            username_emoji = "ayumu"
        elif 'oki' in s:
            username_emoji = "oki"
        elif 'osada' in s:
            username_emoji = "osada"
        elif 'kugi' in s:
            username_emoji = "kugi"
        elif 'kent' in s:
            username_emoji = "kent"
        elif 'saeko' in s:
            username_emoji = "saeko"
        elif 'sanpei' in s:
            username_emoji = "sanpei"
        elif 'nanae' in s:
            username_emoji = "nanae"
        elif 'nanako' in s:
            username_emoji = "nanako"
        elif 'henri' in s:
            username_emoji = "henri"
        elif 'masato' in s:
            username_emoji = "masato"
        elif 'minami' in s:
            username_emoji = "minami"
        elif 'yoshi' in s:
            username_emoji = "yoshi"
        elif 'rina' in s:
            username_emoji = "rina"

        return username_emoji
    except:
        username_emoji = 1000  # エラーとわかりやすくするため1000にしてる
        return username_emoji

    return

# ゲスト数を返す


def if_guest_in(a):
    if '1' in a:
        guest_test = 1
    elif '2' in a:
        guest_test = 2
    elif '3' in a:
        guest_test = 3
    elif '4' in a:
        guest_test = 4
    else:
        guest_test = 0  # 5人以上のときも０にしている

    return guest_test

# どのスタッフのゲストかを返す


def if_userGuest_in(b):
    if 'ayaka' in b:
        username_emoji = "ayaka_guest"
    elif 'ayumu' in b:
        username_emoji = "ayumu_guest"
    elif 'oki' in b:
        username_emoji = "oki_guest"
    elif 'osada' in b:
        username_emoji = "osa_guest"
    elif 'kugi' in b:
        username_emoji = "kugi_guest"
    elif 'kent' in b:
        username_emoji = "kent_guest"
    elif 'saeko' in b:
        username_emoji = "saeko_guest"
    elif 'sanpei' in b:
        username_emoji = "sanpei_guest"
    elif 'nanae' in b:
        username_emoji = "nanae_guest"
    elif 'nanako' in b:
        username_emoji = "nanako_guest"
    elif 'henri' in b:
        username_emoji = "henri_guest"
    elif 'masato' in b:
        username_emoji = "masato_guest"
    elif 'minami' in b:
        username_emoji = "minami_guest"
    elif 'yoshi' in b:
        username_emoji = "yoshi_guest"
    elif 'rina' in b:
        username_emoji = "rina_guest"
    else:
        username_emoji = "name_error_guest"

    return username_emoji

# 集計


def aggregate(fJson):
    howmanySandwich = fJson["sandwich"]
    howmanyhamburger = fJson["hamburger"]
    howmanycurry = fJson["curry"]
    howmanypasta = fJson["pasta"]
    howmanychinese = fJson["chinese"]
    howmanysalad = fJson["salad"]
    howmanyosushi = fJson["osushi"]
    howmanyprotein = fJson["protein"]
    howmanyallok = fJson["allok"]

    howmanystaff = fJson["staff"]
    howmanyGuest = fJson["guest"]
    howmanyormore = fJson["ormore"]

    ayaka = fJson["ayaka"]
    ayumu = fJson["ayumu"]
    osa = fJson["osada"]
    oki = fJson["oki"]
    kugi = fJson["kugi"]
    kent = fJson["kent"]
    saeko = fJson["saeko"]
    sanpei = fJson["sanpei"]
    nanae = fJson["nanae"]
    nanako = fJson["nanako"]
    henri = fJson["henri"]
    masato = fJson["masato"]
    minami = fJson["minami"]
    yoshi = fJson["yoshi"]
    rina = fJson["rina"]
    name_error = fJson["name_error"]
    ormore = fJson["ormore"]

    ayaka_guest = fJson["ayaka_guest"]
    ayumu_guest = fJson["ayumu_guest"]
    osa_guest = fJson["osa_guest"]
    oki_guest = fJson["oki_guest"]
    kugi_guest = fJson["kugi_guest"]
    kent_guest = fJson["kent_guest"]
    saeko_guest = fJson["saeko_guest"]
    sanpei_guest = fJson["sanpei_guest"]
    nanae_guest = fJson["nanae_guest"]
    nanako_guest = fJson["nanako_guest"]
    henri_guest = fJson["henri_guest"]
    masato_guest = fJson["masato_guest"]
    minami_guest = fJson["minami_guest"]
    yoshi_guest = fJson["yoshi_guest"]
    rina_guest = fJson["rina_guest"]

    if ayaka >= 1:
        ayaka_name = 'ayaka:' + str(ayaka_guest)
    elif ayaka == 0:
        ayaka_name = "-"

    if ayumu >= 1:
        ayumu_name = 'ayumu:' + str(ayumu_guest)
    elif ayumu == 0:
        ayumu_name = "-"

    if oki >= 1:
        oki_name = 'oki:' + str(oki_guest)
    elif oki == 0:
        oki_name = "-"

    if osa >= 1:
        osa_name = 'osa:' + str(osa_guest)
    elif osa == 0:
        osa_name = "-"

    if kugi >= 1:
        kugi_name = 'kugi:' + str(kugi_guest)
    elif kugi == 0:
        kugi_name = "-"

    if kent >= 1:
        kent_name = ':kent:' + str(kent_guest)
    elif kent == 0:
        kent_name = "-"

    if saeko >= 1:
        saeko_name = 'saeko:' + str(saeko_guest)
    elif saeko == 0:
        saeko_name = "-"

    if sanpei >= 1:
        sanpei_name = 'sanpei:' + str(sanpei_guest)
    elif sanpei == 0:
        sanpei_name = "-"

    if nanae >= 1:
        nanae_name = 'nanae:' + str(nanae_guest)
    elif nanae == 0:
        nanae_name = "-"

    if nanako >= 1:
        nanako_name = 'nanako:' + str(nanako_guest)
    elif nanako == 0:
        nanako_name = "-"

    if henri >= 1:
        henri_name = 'henri:' + str(henri_guest)
    elif henri == 0:
        henri_name = "-"

    if masato >= 1:
        masato_name = 'masato:' + str(masato_guest)
    elif masato == 0:
        masato_name = "-"

    if minami >= 1:
        minami_name = 'minami:' + str(minami_guest)
    elif minami == 0:
        minami_name = "-"

    if yoshi >= 1:
        yoshi_name = 'yoshi:' + str(yoshi_guest)
    elif yoshi == 0:
        yoshi_name = "-"

    if rina >= 1:
        rina_name = 'rina:' + str(rina_guest)
    elif rina == 0:
        rina_name = "-"

    if name_error >= 1:
        name_error_name = 'エラーのひとがいるよ！:ghost:'
    elif name_error == 0:
        name_error_name = "-"

    if ormore >= 1:
        ormore_name = '5人以上を選んでいる人がいるよ！:ghost:'
    elif ormore == 0:
        ormore_name = "-"

    howmany = "サンドイッチ：" + " *" + str(howmanySandwich) + "*" + "\n"
    howmany += "ハンバーガー：" + " *" + str(howmanyhamburger) + "*" + "\n"
    howmany += "カレー：" + " *" + str(howmanycurry) + "*" + "\n"
    howmany += "パスタ：" + " *" + str(howmanypasta) + "*" + "\n"
    howmany += "中華：" + " *" + str(howmanychinese) + "*" + "\n"
    howmany += "サラダ：" + " *" + str(howmanysalad) + "*" + "\n"
    howmany += "お寿司：" + " *" + str(howmanyosushi) + "*" + "\n"
    howmany += "たんぱく質：" + " *" + str(howmanyprotein) + "*" + "\n"
    howmany += "なんでもいいよ：" + " *" + str(howmanyallok) + "*" + "\n" + "\n"
    howmany += "Staff：" + " *" + str(howmanystaff) + "*" + "\n"
    howmany += "Guest：" + " *" + str(howmanyGuest) + "*" + "\n"
    howmany += ayaka_name + "/" + ayumu_name + "/" + oki_name + "/" + osa_name + "/" + kugi_name + "/" + kent_name + "/" + saeko_name + "/" + sanpei_name + \
        "/" + nanae_name + "/" + nanako_name + "/" + henri_name + "/" + masato_name + \
        "/" + minami_name + "/" + yoshi_name + "/" + rina_name + "\n" + "\n"
    howmany += "Error：" + name_error_name + "\n" + "\n"
    howmany += "5人以上：" + ormore_name + "\n"

    return howmany

# JSONリセット


def json_0(fJson):
    fJson["staff"] = 0

    fJson["sandwich"] = 0
    fJson["hamburger"] = 0
    fJson["curry"] = 0
    fJson["pasta"] = 0
    fJson["chinese"] = 0
    fJson["salad"] = 0
    fJson["osushi"] = 0
    fJson["protein"] = 0
    fJson["allok"] = 0

    fJson["staff"] = 0
    fJson["guest"] = 0
    fJson["ormore"] = 0

    fJson["ayaka"] = 0
    fJson["ayumu"] = 0
    fJson["osa"] = 0
    fJson["oki"] = 0
    fJson["kugi"] = 0
    fJson["kent"] = 0
    fJson["saeko"] = 0
    fJson["sanpei"] = 0
    fJson["nanae"] = 0
    fJson["nanako"] = 0
    fJson["henri"] = 0
    fJson["masato"] = 0
    fJson["minami"] = 0
    fJson["yoshi"] = 0
    fJson["rina"] = 0
    fJson["name_error"] = 0
    fJson["ormore"] = 0
    fJson["ayaka_guest"] = 0
    fJson["ayumu_guest"] = 0
    fJson["osa_guest"] = 0
    fJson["oki_guest"] = 0
    fJson["kugi_guest"] = 0
    fJson["kent_guest"] = 0
    fJson["saeko_guest"] = 0
    fJson["sanpei_guest"] = 0
    fJson["nanae_guest"] = 0
    fJson["nanako_guest"] = 0
    fJson["henri_guest"] = 0
    fJson["masato_guest"] = 0
    fJson["minami_guest"] = 0
    fJson["yoshi_guest"] = 0
    fJson["rina_guest"] = 0

    return fJson
