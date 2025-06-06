from django.db import connections
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
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
                print(
                    "-----------------RESPONSE--------------------\n", response.json()
                )
                return response.json()

            return response.text
        else:
            print("------------------ERROR-------------------\n", response.text)
            try:
                error_data = response.json()
                if (
                    error_data.get("status") == "NotProcessed"
                    and error_data.get("type") == "Validation"
                ):
                    print("Validation error")
                    return {
                        "error": "unauthorized",
                    }
            except Exception as e:
                print(f"Response is not JSON {e}")
                return None
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
        "gmt_offset": "+06:00",
        "preferred_airlines": None,
        "refundable": None,
        "segments": [
            {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
            }
        ],
    }


def get_total_fare_with_markup(
    raw_price: Decimal,
    admin_markup_percentage: Decimal,
    **kwargs,
) -> dict:
    # adding admin markup
    admin_markup_amount = raw_price * (admin_markup_percentage / 100)
    price_with_admin_markup = raw_price + admin_markup_amount

    # adding agent markup
    agent_markup_amount = Decimal(0)

    # if agent_markup_instance is None:
    return {
        "raw_price": raw_price,
        "only_admin_markup": admin_markup_amount,
        "only_agent_markup": agent_markup_amount,
        "price_with_admin_markup": price_with_admin_markup,
        "price_with_agent_markup": price_with_admin_markup,
    }


def create_flight_identifier(search_result: dict) -> str:
    """
    return format:
    BG;BG DAC-CGP;CGP-DAC 2021-09-01;2021-09-02
    """

    segments = search_result["segments"]
    meta_segments = search_result["meta_data"]["segments"]

    airlines = ";".join(seg["airline"]["airline_code"] for seg in segments)
    routes = ";".join(
        f"{seg['origin']['airport_code']}-{seg['destination']['airport_code']}"
        for seg in segments
    )
    departure_dates = ";".join(seg["departure_date"] for seg in meta_segments)

    result = f"{airlines} {routes} {departure_dates}"

    return result


def get_restricted_flights(
    booking_class: str, journey_type: str, flight_start_date: str
) -> list:
    sql_query = """
    SELECT airline_routes_date_identifier
    FROM api_handler_gdsflight 
    WHERE platform = %s    
    AND booking_class = %s
    AND journey_type = %s
    AND flight_start_date = %s;
    """

    params = (
        "mobile",
        booking_class,
        journey_type,
        flight_start_date,
    )

    with connections["secondary"].cursor() as cursor:
        cursor.execute(sql_query, params)
        restricted_flights = [row[0] for row in cursor.fetchall()]

    return restricted_flights
