from django.conf import settings
from django.utils import timezone
import requests
import base64
import redis

# from redis.commands.json.path import Path
# from redis.commands.search.field import TextField, NumericField, TagField
# from redis.commands.search.indexDefinition import IndexDefinition, IndexType
# from requests.auth import HTTPBasicAuth


# Result caching

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
    proxy = f"{settings.PROXY_SERVER_IP}:3128"
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

    print("-----------------PAYLOAD--------------------\n")
    print(url)
    print(headers)
    print(proxies)
    print(data)
    # print("-------------------------------------")

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
                print("-----------------RESPONSE--------------------\n", response.json())
                return response.json()

            return response.text
        else:
            print("------------------ERROR-------------------\n", response.text)
            return None

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


def store_in_redis(data: dict) -> None:
    count = 0

    # get time in milliseconds
    time = int(timezone.now().timestamp() * 1000)
    for entry in data:
        count += 1
        redis_client.json().set(f"flight_cache:{time+count}", "$", entry)

    print("stored ", count)


def remove_all_flights() -> int:
    # Get all keys that match the pattern "flight:*"
    flight_keys = redis_client.keys("flight_cache:*")

    # Delete all keys
    if flight_keys:
        redis_client.delete(*flight_keys)

    return len(flight_keys)


def get_best_match_flight(results: list, target: dict) -> dict:
    # parameters: segments, refundable, total_fare, departure_datetime

    # filter segments and refundable
    filtered_results1 = []
    for result in results:
        if (
            len(result["segments"]) == len(target["segments"])
            and result["is_refundable"] == target["is_refundable"]
        ):
            filtered_results1.append(result)

    # filter closest total_fare
    filtered_results1 = sorted(filtered_results1, key=lambda x: x.get("total_fare", 0))

    for result in filtered_results1:
        # return the first match (greater than or equal to target)
        if result["total_fare"] >= target["total_fare"]:
            return result


ALL_AIRLINES = [
    ("BZL", "CGP"),
    ("BZL", "CXB"),
    ("BZL", "DAC"),
    ("BZL", "JSR"),
    ("BZL", "RJH"),
    ("BZL", "SPD"),
    ("CGP", "BZL"),
    ("CGP", "CXB"),
    ("CGP", "DAC"),
    ("CGP", "JSR"),
    ("CGP", "RJH"),
    ("CGP", "SPD"),
    ("CXB", "BZL"),
    ("CXB", "CGP"),
    ("CXB", "DAC"),
    ("CXB", "JSR"),
    ("CXB", "RJH"),
    ("CXB", "SPD"),
    ("DAC", "BZL"),
    ("DAC", "CGP"),
    ("DAC", "CXB"),
    ("DAC", "JSR"),
    ("DAC", "RJH"),
    ("DAC", "SPD"),
    ("JSR", "BZL"),
    ("JSR", "CGP"),
    ("JSR", "CXB"),
    ("JSR", "DAC"),
    ("JSR", "RJH"),
    ("JSR", "SPD"),
    ("RJH", "BZL"),
    ("RJH", "CGP"),
    ("RJH", "CXB"),
    ("RJH", "DAC"),
    ("RJH", "JSR"),
    ("RJH", "SPD"),
    ("SPD", "BZL"),
    ("SPD", "CGP"),
    ("SPD", "CXB"),
    ("SPD", "DAC"),
    ("SPD", "JSR"),
    ("SPD", "RJH"),
]


def get_search_payload(origin: str, destination: str, departure_date: str) -> dict:
    return {
        "adult_quantity": 1,
        "child_quantity": 0,
        "child_age": 0,
        "infant_quantity": 0,
        "user_ip": "192.46.211.211",
        "journey_type": "Oneway",
        "booking_class": "Economy",
        "segments": [
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
            }
        ],
    }
