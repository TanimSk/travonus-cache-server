from datetime import datetime, timedelta, timezone
from dateutil import parser

# import time
# import json
import xml.etree.ElementTree as ET
from api_handler.sabre import create_session
from api_handler.models import SessionToken
from decimal import Decimal
from api_handler.constants import IATA_AIRPORT_CODE_MAP

# from agent.models import AgentMarkup
from api_handler.utils import get_total_fare_with_markup
from api_handler.constants import AIRLINES_FULL_NAMES

#########
# Sabre #
#########


# -------------------- Air search --------------------


def _return_quantity_dict(search_params: dict):
    passenger_type_array = []

    if search_params["adult_quantity"] > 0:
        passenger_type_array.append(
            {
                "Code": "ADT",
                "Quantity": search_params["adult_quantity"],
                "TPA_Extensions": {
                    "VoluntaryChanges": {"Match": "Info"},
                },
            }
        )
    if search_params["child_quantity"] > 0:
        passenger_type_array.append(
            {
                "Code": f"C{str(search_params['child_age']).zfill(2)}",
                "Quantity": search_params["child_quantity"],
                "TPA_Extensions": {
                    "VoluntaryChanges": {"Match": "Info"},
                },
            }
        )
    if search_params["infant_quantity"] > 0:
        passenger_type_array.append(
            {
                "Code": "INF",
                "Quantity": search_params["infant_quantity"],
                "TPA_Extensions": {
                    "VoluntaryChanges": {"Match": "Info"},
                },
            }
        )
    return passenger_type_array


def air_search_translate(search_params: dict):
    # translated to:
    """
    {
        "OTA_AirLowFareSearchRQ": {
            "Version": "5",
            "POS": {
                "Source": [
                    {
                        "PseudoCityCode": "LQ1L",
                        "RequestorID": {
                            "Type": "1",
                            "ID": "11212",
                            "CompanyName": {
                                "Code": "TN"
                            }
                        }
                    }
                ]
            },
            "OriginDestinationInformation": [
                {
                    "RPH": "1"
                    "DepartureDateTime": "2024-07-13T00:00:00",
                    "OriginLocation": {
                        "LocationCode": "WAW"
                    },
                    "DestinationLocation": {
                        "LocationCode": "SPU"
                    }
                }
            ],
            "TravelPreferences": {
                "DataSources": {
                        "NDC": "Disable",
                        "ATPCO": "Enable",
                        "LCC": "Disable",
                    },
                "PreferNDCSourceOnTie": {"Value": True},

                "TPA_Extensions": {
                    "TripType": {
                        "Value": "OneWay"
                    }
                    // OneWay
                    // Return
                    // Circle
                    // OpenJaw
                    // Other
                },
                "CabinPref": [
                    {
                        "Cabin": "Economy"
                        // PremiumFirst
                        // First
                        // PremiumBusiness
                        // Business
                        // PremiumEconomy
                        // Economy
                    }
                ]
            },
            "TravelerInfoSummary": {
                "AirTravelerAvail": [
                    {
                        "PassengerTypeQuantity": [
                            {
                                "Code": "ADT",
                                "Quantity": 1,
                                "TPA_Extensions": {
                                "VoluntaryChanges": {
                                    "Match": "Info"
                                    }
                                }
                            }
                        ]
                    }
                ]
            },
            "TPA_Extensions": {
                "IntelliSellTransaction": {
                    "RequestType": {
                        "Name": "50ITINS"
                    }
                }
            }
        }
    }
    """

    journey_type_map = {
        "Oneway": "OneWay",
        "Return": "Return",  # Round trip
        "Multicity": "OneWay",
    }

    booking_class_map = {
        "Economy": "Economy",
        "Premium Economy": "PremiumEconomy",
        "Business": "Business",
        "First": "First",
    }

    translated_search_params = {
        "OTA_AirLowFareSearchRQ": {
            "Version": "5",
            "POS": {
                "Source": [
                    {
                        "PseudoCityCode": "LQ1L",
                        "RequestorID": {
                            "Type": "1",
                            "ID": "1",
                            "CompanyName": {"Code": "TN"},
                        },
                    }
                ]
            },
            "TravelPreferences": {
                "TPA_Extensions": {
                    "DataSources": {
                        "NDC": "Disable",
                        "ATPCO": "Enable",
                        "LCC": "Disable",
                    },
                    "PreferNDCSourceOnTie": {"Value": True},
                    "TripType": {
                        "Value": journey_type_map[search_params["journey_type"]]
                    },
                },
                "CabinPref": [
                    {"Cabin": booking_class_map[search_params["booking_class"]]}
                ],
            },
            "OriginDestinationInformation": [],  # Segments
            "TravelerInfoSummary": {
                "AirTravelerAvail": [
                    {
                        "PassengerTypeQuantity": _return_quantity_dict(search_params),
                    }
                ]
            },
            "TPA_Extensions": {
                "IntelliSellTransaction": {"RequestType": {"Name": "50ITINS"}}
            },
        }
    }

    for i, segment in enumerate(search_params["segments"], start=1):
        translated_segment = {
            "RPH": str(i),
            "OriginLocation": {"LocationCode": segment["origin"]},
            "DestinationLocation": {"LocationCode": segment["destination"]},
            "DepartureDateTime": segment["departure_date"] + "T00:00:00",
        }
        translated_search_params["OTA_AirLowFareSearchRQ"][
            "OriginDestinationInformation"
        ].append(translated_segment)

    return translated_search_params


def extract_search_result_ref_obj(target: dict, ref: int):
    return next(
        (item for item in target if item["id"] == ref),
        None,
    )


def search_result_translate(
    results: dict,
    search_params: dict,
    tracing_id: str = None,
    admin_markup: Decimal = None,
    agent_markup_instance=None,
):

    # translated to:
    """
    [
         {
            trace_id: "cd0cd824-c...",
            api_name: "",
            search_id: "",
            result_id: "",
            is_refundable: False,
            seats_available: 1,
            base_price: 1100,
            price_with_admin_markup: 1150,
            total_fare: 1200,
            final_arrival_time: 1626163200,
            duration: 2423,
            inbound_stops: 0,
            outbound_stops: 0,
            airlines: ["UK", "BG"],


            segments: [
                {
                    direction: "outbound", // or inbound
                    origin: {
                        airport_code: "DAC",
                        full_name: "Dhaka",
                        terminal: "",
                        departure_time: 1626163200,
                        gmt_offset_seconds: 3600,
                    },
                    technical_stops: [
                        {
                            airport_code: "KUL",
                            full_name: "Kuala Lumpur",
                            arrival_time: 1626163200,
                            departure_time: 1626163200,
                            gmt_offset_seconds: 3600,
                        }
                    ],
                    destination: {
                        airport_code: "DAC",
                        full_name: "Dhaka",
                        terminal: "",
                        arrival_time: 1626163200,
                        gmt_offset_seconds: 3600,
                    },
                    airline: {
                        validating_flight_number: "184",
                        airline_code: "UK",
                        airline_name: "Vistara",
                        flight_number: "184",
                        "fare_basis": "...",
                        "booking_code": "U",
                    },
                },
            ],

            fare_details: [
                {
                    "pax_type": "Adult",
                    "pax_count": 1,
                    "currency": "BDT",

                    // not addded
                    "base_price": 5719,
                    "discount": 0,
                    "tax": 120,
                    "other_charges": 122,
                    "sub_total_price": 6727
                }
            ]

            // not added
            baggage_details: [
                {
                    segment: "DAC - CXB",
                    check_in_weight: 20,
                    cabin_weight: 7,
                    pax_type: "Adult",
                }
            ]

            "meta_data": search_params
            "validating_carrier": "UK",
        },
    ]
    """

    pax_type_map = {
        "ADT": "Adult",
        "CNN": "Child",
        "INF": "Infant",
    }

    translated_results = []
    # pretty print results

    if (
        results is None
        or results.get("groupedItineraryResponse")["statistics"]["itineraryCount"] == 0
    ):
        return []

    for result in results["groupedItineraryResponse"]["itineraryGroups"][0][
        "itineraries"
    ]:
        # filtering with preferred airlines
        if search_params["preferred_airlines"] is not None:
            if (
                result["pricingInformation"][0]["fare"]["validatingCarrierCode"]
                not in search_params["preferred_airlines"]
            ):
                continue

        # filtering with refundable flights
        if search_params["refundable"] is not None:
            if search_params["refundable"] != (
                not result["pricingInformation"][0]["fare"]["passengerInfoList"][0][
                    "passengerInfo"
                ]["nonRefundable"]
            ):
                continue

        raw_price = Decimal(
            str(result["pricingInformation"][0]["fare"]["totalFare"]["totalPrice"])
        )
        total_fare_with_markup = get_total_fare_with_markup(
            raw_price=raw_price,
            admin_markup_percentage=admin_markup,
            agent_markup_instance=agent_markup_instance,
        )
        # is_return_flight = search_params["journey_type"] == "Return"

        translated_result = {
            "trace_id": tracing_id,
            "api_name": "sabre",
            "search_id": None,
            "result_id": None,
            "is_refundable": not result["pricingInformation"][0]["fare"][  # rethink
                "passengerInfoList"
            ][0]["passengerInfo"]["nonRefundable"],
            # Available seats
            "seats_available": min(
                segment["segment"]["seatsAvailable"] if segment.get("segment") else 9
                for pricing in result["pricingInformation"]
                for passenger_info in pricing["fare"]["passengerInfoList"]
                for component in passenger_info["passengerInfo"]["fareComponents"]
                for segment in component["segments"]
            ),
            # markups
            "only_admin_markup": float(total_fare_with_markup["only_admin_markup"]),
            "only_agent_markup": float(total_fare_with_markup["only_agent_markup"]),
            # pricing details
            "base_price": float(raw_price),
            "price_with_admin_markup": float(
                total_fare_with_markup["price_with_admin_markup"]
            ),
            "total_fare": float(total_fare_with_markup["price_with_agent_markup"]),
            "first_departure_time": 0,
            "final_arrival_time": 0,
            "duration": 0,
            "inbound_stops": 0,
            "outbound_stops": 0,
            "fare_details": [],
            "baggage_details": [],
            "validating_carrier": result["pricingInformation"][0]["fare"][
                "validatingCarrierCode"
            ],
            "airlines": set(),
            "segments": [],
            "meta_data": search_params,
        }

        fare_basis = []
        booking_codes = []
        direction_indicators = []

        # ----------- Add the fare details, fare basises, booking codes -----------
        # TODO: We are just taking the first fare, need to iterate over all fares
        for fare_details in result["pricingInformation"][0]["fare"][
            "passengerInfoList"
        ]:
            translated_fare_details = {
                "pax_type": pax_type_map[
                    (
                        "CNN"
                        if "C" in fare_details["passengerInfo"]["passengerType"]
                        else fare_details["passengerInfo"]["passengerType"]
                    )
                ],
                "pax_count": fare_details["passengerInfo"]["passengerNumber"],
                "currency": result["pricingInformation"][0]["fare"]["totalFare"][
                    "currency"
                ],
                # ------ prices ------
                "base_price": fare_details["passengerInfo"]["passengerTotalFare"][
                    "equivalentAmount"
                ]
                * fare_details["passengerInfo"]["passengerNumber"],
                "discount": "N/A",
                "tax": fare_details["passengerInfo"]["passengerTotalFare"][
                    "totalTaxAmount"
                ]
                * fare_details["passengerInfo"]["passengerNumber"],
                "other_charges": "N/A",
                "sub_total_price": (
                    fare_details["passengerInfo"]["passengerTotalFare"]["totalFare"]
                )
                * fare_details["passengerInfo"]["passengerNumber"],
            }

            translated_result["fare_details"].append(translated_fare_details)

            # Iterate over fare components
            for fare_component in fare_details["passengerInfo"]["fareComponents"]:
                fare_component_description = extract_search_result_ref_obj(
                    results["groupedItineraryResponse"]["fareComponentDescs"],
                    fare_component["ref"],
                )

                # Iterate over segments inside a fare component
                # add booking codes, fare basis and direction indicators
                for segment in fare_component["segments"]:
                    booking_codes.append(
                        segment["segment"]["bookingCode"]
                        if segment.get("segment")
                        else None
                    )
                    fare_basis.append(fare_component_description.get("fareBasisCode"))
                    direction_indicators.append(
                        "outbound"
                        if fare_component_description.get("directionality") == "FROM"
                        else "inbound"
                    )

        # ----------- Add the segments -----------
        segments_ids = (
            []
        )  # [{ref: 1, leg_index: 0, }, {ref: 2, leg_index: 1, departureDateAdjustment: 1, direction: inbound}, ...]
        # is_outbound_flight = True

        for index, leg in enumerate(result["legs"]):
            sub_segments = extract_search_result_ref_obj(
                target=results["groupedItineraryResponse"]["legDescs"],
                ref=leg["ref"],
            ).get("schedules")

            segments_ids.extend(
                [
                    {
                        **data,
                        "leg_index": index,
                        # "direction": "outbound" if is_outbound_flight else "inbound",
                    }
                    for data in sub_segments
                ]
            )

            # if is_return_flight:
            #     is_outbound_flight = False
            #     is_return_flight = False

        legs = results["groupedItineraryResponse"]["itineraryGroups"][0][
            "groupDescription"
        ][
            "legDescriptions"
        ]  # rethink

        for index, segment in enumerate(segments_ids):
            segment_description = extract_search_result_ref_obj(
                results["groupedItineraryResponse"]["scheduleDescs"], segment["ref"]
            )

            # add first departure time
            if index == 0:
                translated_result["first_departure_time"] = _iso_to_unix_local(
                    full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["departure"]["time"]}',
                    offset_days=segment.get("departureDateAdjustment", 0)
                    + segment_description["departure"].get("dateAdjustment", 0),
                    gmtoffset=search_params["gmt_offset"],
                    only_time=True,
                )["only_time"]

            # add final arrival time
            if index == len(segments_ids) - 1:
                translated_result["final_arrival_time"] = _iso_to_unix_local(
                    full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["arrival"]["time"]}',
                    offset_days=segment.get("departureDateAdjustment", 0)
                    + segment_description["arrival"].get("dateAdjustment", 0),
                    gmtoffset=search_params["gmt_offset"],
                    only_time=True,
                )["only_time"]

            # timings
            departure_time = _iso_to_unix_local(
                full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["departure"]["time"]}',
                offset_days=segment.get("departureDateAdjustment", 0)
                + segment_description["departure"].get("dateAdjustment", 0),
                gmtoffset=search_params["gmt_offset"],
            )
            arrival_time = _iso_to_unix_local(
                full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["arrival"]["time"]}',
                offset_days=segment.get("departureDateAdjustment", 0)
                + segment_description["arrival"].get("dateAdjustment", 0),
                gmtoffset=search_params["gmt_offset"],
            )

            translated_segment = {
                "direction": direction_indicators[index],
                "origin": {
                    "airport_code": segment_description["departure"]["airport"],
                    "full_name": IATA_AIRPORT_CODE_MAP.get(
                        segment_description["departure"]["airport"]
                    ),
                    "terminal": segment_description["arrival"].get("terminal"),
                    "departure_time": departure_time["unix_time"],
                    "gmt_offset_seconds": departure_time["gmt_offset_seconds"],
                },
                "technical_stops": [],
                "destination": {
                    "airport_code": segment_description["arrival"]["airport"],
                    "full_name": IATA_AIRPORT_CODE_MAP.get(
                        segment_description["arrival"]["airport"]
                    ),
                    "terminal": segment_description["arrival"].get("terminal"),
                    "arrival_time": arrival_time["unix_time"],
                    "gmt_offset_seconds": arrival_time["gmt_offset_seconds"],
                },
                "airline": {
                    "marketing_airline_code": segment_description["carrier"][
                        "marketing"
                    ],
                    "marketing_flight_number": segment_description["carrier"][
                        "marketingFlightNumber"
                    ],
                    "airline_code": segment_description["carrier"]["operating"],
                    # segment_description["carrier"]["equipment"]["code"]
                    "airline_name": AIRLINES_FULL_NAMES.get(
                        segment_description["carrier"]["operating"],
                        "",
                    ),
                    "flight_number": segment_description["carrier"][
                        "operatingFlightNumber"
                    ],
                    "fare_basis": (
                        fare_basis[index] if index < len(fare_basis) else None
                    ),
                    "booking_code": booking_codes[index],
                },
            }

            # Add technical stops
            if segment_description.get("hiddenStops", None):
                for technical_stop in segment_description["hiddenStops"]:
                    departure_time = _iso_to_unix_local(
                        full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{technical_stop["departureTime"]}',
                        offset_days=technical_stop.get("departureDateAdjustment", 0),
                        gmtoffset=search_params["gmt_offset"],
                    )
                    arrival_time = _iso_to_unix_local(
                        full_time_string=f'{legs[segment["leg_index"]]["departureDate"]}T{technical_stop["arrivalTime"]}',
                        offset_days=technical_stop.get("arrivalDateAdjustment", 0),
                        gmtoffset=search_params["gmt_offset"],
                    )
                    translated_segment["technical_stops"].append(
                        {
                            "airport_code": technical_stop["airport"],
                            "full_name": IATA_AIRPORT_CODE_MAP.get(
                                technical_stop["airport"]
                            ),
                            "arrival_time": arrival_time["unix_time"],
                            "departure_time": departure_time["unix_time"],
                            "gmt_offset_seconds": arrival_time["gmt_offset_seconds"],
                        }
                    )

            translated_result["segments"].append(translated_segment)

            # add airlines
            translated_result["airlines"].add(
                segment_description["carrier"]["operating"]
            )

            # update stops
            translated_result["outbound_stops"] += (
                1 if translated_segment["direction"] == "outbound" else 0
            )
            translated_result["inbound_stops"] += (
                1 if translated_segment["direction"] == "inbound" else 0
            )

        # check flight is return or not
        segment_length = (
            len(translated_result["meta_data"]["segments"])
            if not search_params["journey_type"] == "Return"
            else len(search_params["segments"]) / 2
        )

        # modify stops
        if translated_result["inbound_stops"] > 0:
            translated_result["inbound_stops"] = int(
                translated_result["inbound_stops"] - segment_length
            )
        if translated_result["outbound_stops"] > 0:
            translated_result["outbound_stops"] = int(
                translated_result["outbound_stops"] - segment_length
            )

        # ----------- Add the baggage details -----------
        for index, fare_details in enumerate(
            result["pricingInformation"][0]["fare"]["passengerInfoList"]
        ):
            pax_type = translated_result["fare_details"][index]["pax_type"]

            for baggage in fare_details["passengerInfo"]["baggageInformation"]:
                for segment in baggage["segments"]:

                    baggage_info = extract_search_result_ref_obj(
                        target=results["groupedItineraryResponse"][
                            "baggageAllowanceDescs"
                        ],
                        ref=baggage["allowance"]["ref"],
                    )

                    check_in_weight = (
                        f"{baggage_info.get('weight')} {baggage_info.get('unit')}"
                        if not baggage_info.get("pieceCount", None)
                        else f"{baggage_info.get('pieceCount') * 23} KG"
                    )

                    translated_result["baggage_details"].append(
                        {
                            "segment": f"{translated_result['segments'][segment['id']]['origin']['airport_code']} - {translated_result['segments'][segment['id']]['destination']['airport_code']}",
                            "check_in_weight": check_in_weight,
                            "cabin_weight": "7 KG",
                            "pax_type": pax_type,
                        }
                    )

        # last arrival time - first departure time
        translated_result["duration"] = (
            translated_result["segments"][-1]["destination"]["arrival_time"]
            - translated_result["segments"][0]["origin"]["departure_time"]
        )

        # convert airlines set to list
        translated_result["airlines"] = list(translated_result["airlines"])

        translated_results.append(translated_result)

    return translated_results


# -------------------- Air rules --------------------
def air_rules_inject_translate(rules_params: dict):
    # translated to:
    """
    [
        {
            route: "DAC - CXB",
            xml: "<xml>"
        }
    ]
    """
    seesion_token = SessionToken.objects.last().token
    xml_bodies = []

    for segments in rules_params["segments"]:
        departure_date = _unix_to_iso_date(segments["origin"]["departure_time"])
        origin = segments["origin"]["airport_code"]
        airline_name = segments["airline"]["airline_name"]
        destination = segments["destination"]["airport_code"]
        fare_basis = segments["airline"]["fare_basis"]

        xml_bodies.append(
            {
                "route": f"{origin} - {destination}",
                "xml": f"""
            {create_session.xml_header(seesion_token)}
            <OTA_AirRulesRQ ReturnHostCommand="true" Version="2.3.0" xmlns="http://webservices.sabre.com/sabreXML/2011/10" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <OriginDestinationInformation>
                    <FlightSegment DepartureDateTime="{departure_date}">
                        <DestinationLocation LocationCode="{destination}"/>
                        <MarketingCarrier Code="{airline_name}"/>
                        <OriginLocation LocationCode="{origin}"/>
                    </FlightSegment>
                </OriginDestinationInformation>
                <RuleReqInfo>
                    <FareBasis Code="{fare_basis}"/>                    
                </RuleReqInfo>
            </OTA_AirRulesRQ>
            {create_session.xml_footer()}
            """,
            }
        )

    return xml_bodies


# ---------------------- Air Rules ----------------------


def extract_rules(xml_string):
    # Parse the XML string
    root = ET.fromstring(xml_string)

    # Define namespaces
    namespaces = {
        "soap-env": "http://schemas.xmlsoap.org/soap/envelope/",
        "eb": "http://www.ebxml.org/namespaces/messageHeader",
        "wsse": "http://schemas.xmlsoap.org/ws/2002/12/secext",
        "sabre": "http://webservices.sabre.com/sabreXML/2011/10",
        "stl": "http://services.sabre.com/STL/v01",
    }

    # Find all paragraphs with the rules
    paragraphs = root.findall(".//sabre:Paragraph", namespaces)

    # Extract and store the rules
    rules = []
    for paragraph in paragraphs:
        # rph = paragraph.get('RPH')
        title = paragraph.get("Title")
        text = (
            paragraph.find("sabre:Text", namespaces).text.strip()
            if paragraph.find("sabre:Text", namespaces) is not None
            else ""
        )
        rules.append(f"{title}\n\n{text}")

    return rules


def air_rules_result_translate(rules_params: dict):
    # translated to:
    """
    [
        {
            route: "DAC - CXB",
            rule_details: [...]
        }
    ]
    """
    translated_rules = []

    for rules in rules_params:
        translated_rules.append(
            {
                "route": rules["route"],
                "rule_details": extract_rules(rules["body"]),
            }
        )

    return translated_rules


def air_rules_mini_inject_translate(rules_params: dict) -> dict:
    # same as air_rules_inject_translate
    return air_pricing_details_inject_translate(pricing_params=rules_params)


def air_rules_mini_result_translate(rules_params: dict, meta_data: dict) -> dict:
    # translated to:
    """
    {
        "cancellation": [
            {
                "pax_type": "Adult",
                "city_pair": "DAC - CXB",
                "type": "Before Departure",
                "info": "description",
            }
        ]
        "date_change": [
            {
                "pax_type": "Adult",
                "city_pair": "DAC - CXB",
                "type": "Before Departure",
                "info": "description",
            }
        ]
    }
    """

    if (
        rules_params is None
        or rules_params.get("groupedItineraryResponse")["statistics"]["itineraryCount"]
        == 0
    ):
        return []

    translated_rules = {
        "cancellation": [],
        "date_change": [],
    }

    city_pairs = f"{meta_data["segments"][0]['origin']} - {meta_data['segments'][-1]['destination']}"

    rules_list = rules_params["groupedItineraryResponse"]["itineraryGroups"][0][
        "itineraries"
    ][0]["pricingInformation"][0]["fare"]["passengerInfoList"]

    for rule in rules_list:
        pax_type = (
            "Adult"
            if "ADT" in rule["passengerInfo"]["passengerType"]
            else (
                "Child" if "INF" in rule["passengerInfo"]["passengerType"] else "Child"
            )
        )

        for penalty in rule["passengerInfo"]["penaltiesInfo"]["penalties"]:
            if penalty["type"] == "Refund":
                translated_rules["cancellation"].append(
                    {
                        "pax_type": pax_type,
                        "city_pair": city_pairs,
                        "type": penalty["applicability"],
                        "info": (
                            f"Amount: {penalty["amount"]} {penalty["currency"]} <br> Minimum: {penalty["minPenalty"]["amount"]} {penalty["currency"]}"
                            if penalty["refundable"]
                            else "Not Refundable"
                        ),
                    }
                )

            elif penalty["type"] == "Exchange":
                translated_rules["date_change"].append(
                    {
                        "pax_type": pax_type,
                        "city_pair": city_pairs,
                        "type": penalty["applicability"],
                        "info": (
                            f"Amount: {penalty["amount"]} {penalty["currency"]} <br> Minimum: {penalty["minPenalty"]["amount"]} {penalty["currency"]}"
                            if penalty["changeable"]
                            else "Not Changeable"
                        ),
                    }
                )

    return translated_rules


# -------------------- Air pricing details --------------------


def air_pricing_details_inject_translate(pricing_params: dict):
    # translated to:
    """
    {
        "OTA_AirLowFareSearchRQ": {
            "Version": "5",
            "TravelPreferences": {
                "TPA_Extensions": {
                    "VerificationItinCallLogic": {
                        "Value": "L"
                    }
                }
            },
            "TravelerInfoSummary": {
                "SeatsRequested": [
                    1
                ],
                "AirTravelerAvail": [
                    {
                        "PassengerTypeQuantity": [
                            {
                                "Code": "ADT",
                                "Quantity": 1
                            }
                        ]
                    }
                ]
            },
            "POS": {
                "Source": [
                    {
                        "PseudoCityCode": "LQ1L",
                        "RequestorID": {
                            "Type": "1",
                            "ID": "1",
                            "CompanyName": {
                                "Code": "TN"
                            }
                        }
                    }
                ]
            },
            "OriginDestinationInformation": [
                {
                    "RPH": "1",
                    "DepartureDateTime": "2024-08-10T00:00:00",
                    "OriginLocation": {
                        "LocationCode": "DAC"
                    },
                    "DestinationLocation": {
                        "LocationCode": "CXB"
                    },
                    "TPA_Extensions": {
                        "SegmentType": {
                            "Code": "O"
                        },
                        "Flight": [
                            {
                                "Number": 141,
                                "DepartureDateTime": "2024-08-10T00:00:00",
                                "ArrivalDateTime": "2024-08-10T00:00:00",
                                "Type": "A",
                                "ClassOfService": "K",
                                "OriginLocation": {
                                    "LocationCode": "DAC"
                                },
                                "DestinationLocation": {
                                    "LocationCode": "CXB"
                                },
                                "Airline": {
                                    "Operating": "BS",
                                    "Marketing": "BS"
                                }
                            }
                        ]
                    }
                }
            ],
            "TPA_Extensions": {
                "IntelliSellTransaction": {
                    "RequestType": {
                        "Name": "50ITINS"
                    }
                }
            }
        }
    }

    """

    translated_pricing_params = {
        "OTA_AirLowFareSearchRQ": {
            "Version": "5",
            "POS": {
                "Source": [
                    {
                        "PseudoCityCode": "LQ1L",
                        "RequestorID": {
                            "Type": "1",
                            "ID": "1",
                            "CompanyName": {"Code": "TN"},
                        },
                    }
                ]
            },
            "TravelPreferences": {
                "TPA_Extensions": {
                    "VerificationItinCallLogic": {"Value": "L"},
                }
            },
            "TravelerInfoSummary": {
                "SeatsRequested": [
                    pricing_params["meta_data"]["adult_quantity"]
                    + pricing_params["meta_data"]["child_quantity"]
                ],
                "AirTravelerAvail": [
                    {
                        "PassengerTypeQuantity": _return_quantity_dict(
                            pricing_params["meta_data"]
                        ),
                    }
                ],
            },
            "OriginDestinationInformation": [],
            "TPA_Extensions": {
                "IntelliSellTransaction": {"RequestType": {"Name": "50ITINS"}}
            },
        }
    }

    # TODO: add parent segment here!
    for index, segment in enumerate(pricing_params["segments"]):
        translated_segment = {
            "RPH": str(index + 1),
            "DepartureDateTime": _unix_to_iso_datetime(
                segment["origin"]["departure_time"]
                + segment["origin"]["gmt_offset_seconds"]
            ),
            "OriginLocation": {"LocationCode": segment["origin"]["airport_code"]},
            "DestinationLocation": {
                "LocationCode": segment["destination"]["airport_code"]
            },
            "TPA_Extensions": {
                "SegmentType": {"Code": "O"},
                # TODO: rethink here, there could be more segments
                "Flight": [
                    {
                        "Number": segment["airline"]["flight_number"],
                        "DepartureDateTime": _unix_to_iso_datetime(
                            segment["origin"]["departure_time"]
                            + segment["origin"]["gmt_offset_seconds"]
                        ),
                        "ArrivalDateTime": _unix_to_iso_datetime(
                            segment["destination"]["arrival_time"]
                            + segment["destination"]["gmt_offset_seconds"]
                        ),
                        "Type": "A",
                        "ClassOfService": "K",
                        "OriginLocation": {
                            "LocationCode": segment["origin"]["airport_code"]
                        },
                        "DestinationLocation": {
                            "LocationCode": segment["destination"]["airport_code"]
                        },
                        "Airline": {
                            "Operating": segment["airline"]["airline_code"],
                            "Marketing": pricing_params["validating_carrier"],
                        },
                    }
                ],
            },
        }

        translated_pricing_params["OTA_AirLowFareSearchRQ"][
            "OriginDestinationInformation"
        ].append(translated_segment)

    return translated_pricing_params


def air_pricing_details_result_translate(
    results: dict,
    search_params: dict,
    admin_markup: Decimal = None,
    agent_markup_instance=None,
):
    return search_result_translate(
        results=results,
        search_params=search_params,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )


def flight_booking_inject_translate(booking_params: dict):
    # translated to:
    """
    documentation: https://developer.sabre.com/docs/rest_apis/air/book/create_passenger_name_record

    {
        "CreatePassengerNameRecordRQ": {
            "version": "2.5.0",
            "TravelItineraryAddInfo": {
                "AgencyInfo": {
                    "Ticketing": {
                        "TicketType": "7TAW"
                    }
                },
                "CustomerInfo": {
                    "ContactNumbers": {
                        "ContactNumber": [
                            {
                                "Phone": "74991234567",
                                "PhoneUseType": "A"
                            }
                        ]
                    },
                    "PersonName": [
                        {
                            "NameNumber": "1.1",
                            "GivenName": "MAX",
                            "Surname": "POWER"
                        }
                    ]
                }
            },
            "AirBook": {
                "OriginDestinationInformation": {
                    "FlightSegment": [
                        {
                            "DepartureDateTime": "{{start_date}}T00:00:00",
                            "FlightNumber": "203",
                            "NumberInParty": "1",
                            "ResBookDesigCode": "Y",
                            "Status": "NN",
                            "DestinationLocation": {
                                "LocationCode": "LAS"
                            },
                            "MarketingAirline": {
                                "Code": "UA",
                                "FlightNumber": "203"
                            },
                            "OriginLocation": {
                                "LocationCode": "ORD"
                            }
                        }
                    ]
                },
                "RedisplayReservation": {"NumAttempts": 3, "WaitInterval": 3000},
            },

            "SpecialReqDetails": {
                "SpecialService": {
                    "SpecialServiceInfo": {
                        "AdvancePassenger": [
                            {
                                "SegmentNumber": "A",
                                "Document": {
                                    "Number": "FB27101349",
                                    "ExpirationDate": "2026-01-05",
                                    "Type": "P",
                                    "IssueCountry": "SG",
                                    "NationalityCountry": "SG",
                                },
                                "PersonName": {
                                    "NameNumber": "1.1",
                                    "GivenName": "Alex",
                                    "Surname": "Jones",
                                    "Gender": "M",
                                    "DateOfBirth": "1967-11-26",
                                },
                            }
                        ],
                    }
                }
            },

            "MiscSegment": {
                "OriginLocation": {
                    "LocationCode": "LAX"
                },
                "Text": "OTH MISCELLANEOUS SEGMENT",
                "VendorPrefs": {
                    "Airline": {
                        "Code": "B6"
                    }
                },
                "DepartureDateTime": "09-08",
                "NumberInParty": 1,
                "Status": "GK",
                "Type": "OTH"
            },
            "PostProcessing": {
                "RedisplayReservation": {
                    "waitInterval": 100,
                    "returnExtendedPriceQuote": True,
                },
                "EndTransaction": {
                    "Source": {"ReceivedFrom": "SabreAPIs"},
                },
            },
        }
    }
    """

    pax_type_map = {
        "Adult": "ADT",
        "Child": "CNN",
        "Infant": "INF",
    }

    translated_booking_params = {
        "CreatePassengerNameRecordRQ": {
            "version": "2.5.0",
            "TravelItineraryAddInfo": {
                "AgencyInfo": {"Ticketing": {"TicketType": "7TAW"}},
                "CustomerInfo": {
                    "ContactNumbers": {"ContactNumber": []},
                    "Email": [],
                    "PersonName": [],
                },
            },
            "AirBook": {
                "HaltOnStatus": [
                    {"Code": "NO"},
                    {"Code": "NN"},
                    {"Code": "UC"},
                    {"Code": "US"},
                    {"Code": "UN"},
                    {"Code": "LL"},
                    {"Code": "HL"},
                    {"Code": "HX"},
                    {"Code": "WL"},
                ],
                "OriginDestinationInformation": {
                    "FlightSegment": [],
                },
                "RedisplayReservation": {"NumAttempts": 3, "WaitInterval": 3000},
            },
            "AirPrice": [
                {
                    "PriceRequestInformation": {
                        "Retain": True,
                        "OptionalQualifiers": {
                            "PricingQualifiers": {
                                "PassengerType": [
                                    # {"Quantity": "1", "Code": "ADT"}
                                ]
                            }
                        },
                    }
                }
            ],
            "SpecialReqDetails": {
                "SpecialService": {
                    "SpecialServiceInfo": {
                        "AdvancePassenger": [],
                        "Service": [
                            {
                                "SegmentNumber": "A",
                                "SSR_Code": "CTCM",
                                "PersonName": {"NameNumber": "1.1"},
                                "Text": "N/A",
                            },
                            {
                                "SegmentNumber": "A",
                                "SSR_Code": "CTCE",
                                "PersonName": {"NameNumber": "1.1"},
                                "Text": "N/A",
                            },
                        ],
                        "SecureFlight": [
                            {
                                "PersonName": {
                                    "Gender": (
                                        "M"
                                        if booking_params["lead_passenger_info"][
                                            "gender"
                                        ]
                                        == "Male"
                                        else "F"
                                    ),
                                    "GivenName": booking_params["lead_passenger_info"][
                                        "first_name"
                                    ],
                                    "Surname": booking_params["lead_passenger_info"][
                                        "last_name"
                                    ],
                                    "DateOfBirth": booking_params[
                                        "lead_passenger_info"
                                    ]["birth_date"],
                                    "NameNumber": "1.1",
                                },
                                "SegmentNumber": "A",
                                "VendorPrefs": {"Airline": {"Hosted": False}},
                            }
                        ],
                    },
                },
            },
            "PostProcessing": {
                "RedisplayReservation": {
                    "waitInterval": 100,
                    "returnExtendedPriceQuote": True,
                },
                "EndTransaction": {
                    "Source": {"ReceivedFrom": "SabreAPIs"},
                },
            },
        }
    }

    # ---------------------- Customer Info ----------------------

    # add contact number
    translated_booking_params["CreatePassengerNameRecordRQ"]["TravelItineraryAddInfo"][
        "CustomerInfo"
    ]["ContactNumbers"]["ContactNumber"].append(
        {
            "Phone": booking_params["lead_passenger_info"]["contact_number"],
            "PhoneUseType": "H",
        }
    )

    all_pax = booking_params["other_passengers_info"] + [
        booking_params["lead_passenger_info"]
    ]

    passenger_type_dict = {
        "Adult": 0,
        "Child": 0,
        "Infant": 0,
    }

    # Adding pax info
    for index, passenger in enumerate(all_pax):

        # add email
        translated_booking_params["CreatePassengerNameRecordRQ"][
            "TravelItineraryAddInfo"
        ]["CustomerInfo"]["Email"].append(
            {
                "NameNumber": f"{index + 1}.1",
                "Address": passenger["email"],
                "Type": "CC",
            }
        )

        # add name, pax type
        translated_booking_params["CreatePassengerNameRecordRQ"][
            "TravelItineraryAddInfo"
        ]["CustomerInfo"]["PersonName"].append(
            {
                "NameNumber": f"{index + 1}.1",
                "GivenName": passenger["first_name"],
                "Surname": passenger["last_name"],
                "Infant": passenger["pax_type"] == "Infant",
                # "NameReference": "",
                "PassengerType": (
                    pax_type_map[passenger["pax_type"]]
                    if not passenger["pax_type"] == "Child"
                    else f'C{str(booking_params["flight_ref"]["meta_data"]["child_age"]).zfill(2)}'
                ),
            }
        )

        # update passenger_type_dict
        passenger_type_dict[passenger["pax_type"]] += 1

        # add passenger info
        if passenger["passport_number"] != "":
            translated_booking_params["CreatePassengerNameRecordRQ"][
                "SpecialReqDetails"
            ]["SpecialService"]["SpecialServiceInfo"]["AdvancePassenger"].append(
                {
                    "SegmentNumber": "A",
                    "Document": {
                        "Number": passenger["passport_number"],
                        "ExpirationDate": passenger["passport_expiry_date"],
                        "Type": "P",
                        "IssueCountry": passenger["passport_nationality"],
                        "NationalityCountry": passenger["passport_nationality"],
                    },
                    "PersonName": {
                        "NameNumber": f"{index + 1}.1",
                        "GivenName": passenger["first_name"],
                        "Surname": passenger["last_name"],
                        "Gender": "M" if passenger["gender"] == "Male" else "F",
                        "DateOfBirth": passenger["birth_date"],
                    },
                }
            )

    # ---------------------- Update PricingQualifiers ---------
    for passenger_type in passenger_type_dict.keys():
        if passenger_type_dict[passenger_type] > 0:
            translated_booking_params["CreatePassengerNameRecordRQ"]["AirPrice"][0][
                "PriceRequestInformation"
            ]["OptionalQualifiers"]["PricingQualifiers"]["PassengerType"].append(
                {
                    "Quantity": str(passenger_type_dict[passenger_type]),
                    "Code": (
                        pax_type_map[passenger_type]
                        if passenger_type != "Child"
                        else f'C{str(booking_params["flight_ref"]["meta_data"]["child_age"]).zfill(2)}'
                    ),
                }
            )

    # ---------------------- Flight Info ----------------------
    for index, segment in enumerate(booking_params["flight_ref"]["segments"]):

        translated_booking_params["CreatePassengerNameRecordRQ"]["AirBook"][
            "OriginDestinationInformation"
        ]["FlightSegment"].append(
            {
                "DepartureDateTime": _unix_to_iso_datetime(
                    segment["origin"]["departure_time"]
                    + segment["origin"]["gmt_offset_seconds"]
                ),
                "ArrivalDateTime": _unix_to_iso_datetime(
                    segment["destination"]["arrival_time"]
                    + segment["destination"]["gmt_offset_seconds"]
                ),
                "FlightNumber": str(segment["airline"]["flight_number"]),
                "NumberInParty": str(
                    sum(p["pax_type"] in ["Adult", "Child"] for p in all_pax)
                ),
                "ResBookDesigCode": segment["airline"]["booking_code"],
                "Status": "NN",
                "OriginLocation": {
                    "LocationCode": segment["origin"]["airport_code"],
                },
                "MarriageGrp": "O",
                "DestinationLocation": {
                    "LocationCode": segment["destination"]["airport_code"]
                },
                "OperatingAirline": {
                    "Code": segment["airline"]["airline_code"],
                },
                "MarketingAirline": {
                    "Code": segment["airline"]["marketing_airline_code"],
                    "FlightNumber": str(segment["airline"]["marketing_flight_number"]),
                },
            }
        )

    return translated_booking_params


def flight_pre_booking_result_translate(
    booking_params: dict,
    meta_data: dict,
    admin_markup: Decimal,
    agent_markup_instance=None,
):
    if booking_params is None:
        return {
            "__error": "You cannot pre-book this flight. Please try another flight."
        }

    return search_result_translate(
        results=booking_params,
        search_params=meta_data,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )


def flight_booking_result_translate(
    booking_params: dict,
    response: dict,
    admin_markup: Decimal,
    agent_markup_instance=None,
):

    return [
        {
            "pnr": response["CreatePassengerNameRecordRS"]["ItineraryRef"]["ID"],
            **booking_params["flight_ref"],
        }
    ]


# def _iso_to_unix_local(full_time_string, offset_days=0):
#     # output: 1626163200 // seconds

#     """
#     Returns the local time, e.g. 2024-11-01T18:45:00+06:00
#     will return unix equivalent of: November 1, 2024, at 06:45 PM
#     """

#     datetime_obj = parser.isoparse(full_time_string)
#     unix_time = int(datetime_obj.timestamp())

#     # convert days to seconds
#     # 24 hours * 60 minutes * 60 seconds
#     offset_seconds = offset_days * 86400
#     unix_time += offset_seconds

#     return unix_time


def _iso_to_unix_local(
    full_time_string, offset_days=0, gmtoffset="+00:00", only_time=False
) -> dict:
    """
    Input: 2024-11-01T18:45:00+06:00
    Returns the Unix time equivalent in the Bangladesh timezone (UTC+6).
    """

    # Parse the ISO format time string
    datetime_obj = parser.isoparse(full_time_string)

    # Define Bangladesh's timezone (UTC+6)
    user_timezone = timezone(
        timedelta(
            hours=int(gmtoffset[1:3]) if gmtoffset[0] == "+" else -int(gmtoffset[1:3])
        )
    )

    # Convert the datetime object to Bangladesh timezone
    datetime_user = datetime_obj.astimezone(user_timezone)

    if only_time:
        # Extract the time and calculate seconds since midnight
        midnight = datetime_user.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_since_midnight = (datetime_user - midnight).seconds
        return {
            "only_time": seconds_since_midnight,
        }

    unix_time = int(datetime_user.timestamp())
    # Convert offset days to seconds and add to Unix time
    offset_seconds = offset_days * 86400
    unix_time += offset_seconds

    return {
        "unix_time": unix_time,
        "gmt_offset_seconds": int(datetime_obj.utcoffset().total_seconds()),
    }


def _unix_to_iso_date(unix_time):
    # output: 2023-09-20
    return datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%d")


def _unix_to_iso_datetime(unix_time):
    # output: 2023-09-20T12:35:00
    return datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%dT%H:%M:%S")


# x = json.load(open("./api_handler/sabre/resp.json"))
# print(
#     json.dumps(
#         search_result_translate(
#             results=x, search_params={}, tracing_id="", admin_markup=Decimal("0")
#         ),
#         indent=4,
#     )
# )
