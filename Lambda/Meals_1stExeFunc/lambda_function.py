import os
import re
import json
import logging
import boto3
from urllib.parse import parse_qs

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # 受け取ったイベント情報をCloud Watchログに出力
    logging.info(json.dumps(event))

    input_event = {
        "event": event,
    }

    Payload = json.dumps(input_event)  # jsonシリアライズ

    # 呼び出し
    response = boto3.client('lambda').invoke(
        FunctionName='test_201011',
        InvocationType='Event',
        Payload=Payload
    )

    return {
        'statusCode': 200,
    }
