from requests.auth import HTTPBasicAuth
from django.conf import settings
import requests
import base64

import redis
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

# import json


redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)


def call_external_api(
    url: str, data=None, ssl=True, method="POST", content: str = "json", **kwargs
):
    # remove this on production
    proxy = "192.46.211.211:3128"
    proxy_auth = base64.b64encode(
        f"{settings.PROXY_SERVER_USERNAME}:{settings.PROXY_SERVER_PASSWORD}".encode()
    ).decode()

    proxies = (
        {
            "http": f"http://{proxy}",
            "https": f"https://{proxy}",
        }
        if ssl
        else {
            "http": f"http://{proxy}",
        }
    )

    headers = kwargs.get("headers", {})
    headers["Content-Type"] = headers.get("Content-Type", "application/json")
    headers["Proxy-Authorization"] = f"Basic {proxy_auth}"
    print(proxies)
    print(data)

    try:
        if method == "POST":
            response = requests.post(
                url,
                **{"json" if content == "json" else "data": data},
                proxies=proxies,
                headers=headers,
                # auth=auth,
                # verify=False,
            )
        elif method == "GET":
            response = requests.get(
                url,
                proxies=proxies,
                headers=headers,
                # auth=auth,
                # verify=False,
            )
        else:
            print(f"Unsupported method: {method}")
            return None

        if response.status_code == 200:

            if "application/json" in response.headers.get("content-type"):
                print("-------------------------------------\n", response.json())
                return response.json()

            return response.text
        else:
            print("-------------------------------------\n", response.text)
            return None

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


def store_in_redis(data: dict) -> None:
    count = 0

    for entry in data:
        count += 1
        redis_client.json().set(f"flight_cache:{count}", "$", entry)

    print("stored ", count)


def remove_all_flights() -> int:
    # Get all keys that match the pattern "flight:*"
    flight_keys = redis_client.keys("flight_cache:*")

    # Delete all keys
    if flight_keys:
        redis_client.delete(*flight_keys)

    return len(flight_keys)
