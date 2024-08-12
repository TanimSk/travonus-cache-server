from datetime import datetime, timezone
from dateutil import parser
import time

##########
# BDfare #
##########


# ---------------------- Air Search ----------------------


def _return_passenger_dict(search_params: dict):
    passenger_type_array = []

    passenger_id = 0

    for _ in range(search_params["adult_quantity"]):
        passenger_id += 1
        passenger_type_array.append({"ptc": "ADT", "paxID": f"PAX{passenger_id}"})

    for _ in range(search_params["child_quantity"]):
        passenger_id += 1
        passenger_type_array.append(
            {
                "ptc": f"C{str(search_params['child_age']).zfill(2)}",
                "paxID": f"PAX{passenger_id}",
            }
        )

    for _ in range(search_params["infant_quantity"]):
        passenger_id += 1
        passenger_type_array.append({"ptc": "INF", "paxID": f"PAX{passenger_id}"})

    return passenger_type_array


def air_search_translate(search_params: dict):
    # translated to:
    """
    {
        "pointOfSale": "BD",
        "request": {
            "originDest": [
                {
                    "originDepRequest": {
                        "iatA_LocationCode": "DAC",
                        "date": "2024-07-25"
                    },
                    "destArrivalRequest": {
                        "iatA_LocationCode": "CXB"
                    }
                }
            ],
            "pax": [
                {
                    "paxID": "PAX1",
                    "ptc": "ADT"
                },
                // Child of 3 years old
                {
                    "paxID": "PAX2",
                    "ptc": "C03"
                }
            ],
            "shoppingCriteria": {
                "tripType": "Oneway",
                // Oneway
                // Return
                // Circle

                "travelPreferences": {
                    // "vendorPref": [
                    //     "BG" // airline code
                    // ],
                    "cabinCode": "Economy"
                    // Economy
                    // PremiumEconomy
                    // Business
                    // First
                },
                "returnUPSellInfo": true
            }
        }
    }
    """

    journey_type_map = {
        "Oneway": "OneWay",
        "Return": "Return",  # Round trip
        "Multicity": "Circle",
    }

    booking_class_map = {
        "Economy": "Economy",
        "Premium Economy": "PremiumEconomy",
        "Business": "Business",
        "First": "First",
    }

    translated_search_params = {
        "pointOfSale": "BD",
        "request": {
            "originDest": [],
            "pax": _return_passenger_dict(search_params),
            "shoppingCriteria": {
                "tripType": journey_type_map[search_params["journey_type"]],
                "travelPreferences": {
                    "cabinCode": booking_class_map[search_params["booking_class"]],
                },
                "returnUPSellInfo": True,
            },
        },
    }

    for segment in search_params["segments"]:
        translated_segment = {
            "originDepRequest": {
                "iatA_LocationCode": segment["origin"],
                "date": segment["departure_date"],
            },
            "destArrivalRequest": {"iatA_LocationCode": segment["destination"]},
        }
        translated_search_params["request"]["originDest"].append(translated_segment)

    return translated_search_params


def search_result_translate(results: dict, search_params: dict):

    # translated to:
    """
    [
        {
            api_name: "",
            search_id: "",
            result_id: "",
            is_refundable: False,
            seats_available: 1,
            total_fare: 1200,

            validating_carrier: "UK",

            segments: [
            {
                origin: {
                    airport_code: "DAC",
                    terminal: "",
                    departure_time: "2024-07-20T11:45:00",
                },
                distination: {
                    airport_code: "DAC",
                    terminal: "",
                    arrival_time: "2024-07-20T11:45:00",
                },
                airline: {
                    airline_code: "UK",
                    airline_name: "Vistara",
                    flight_number: "184",
                    fare_basis: "",
                },
            },
            ],

            fare_details: [
                {
                    "pax_type": "Adult",
                    "pax_count": 1,
                    "currency": "BDT",

                    "base_price": 5719,
                    "discount": 0,
                    "tax": 120,
                    "other_charges": 122,
                    "sub_total_price": 6727
                }
            ]

            baggage_details: [
                {
                    segment: "DAC - CXB",
                    check_in_weight: 20,
                    cabin_weight: 7,
                    pax_type: "Adult",
                }
            ]

            meta_data: search_params
        },
    ]
    """

    print(results)

    translated_results = []

    if (
        results is None
        or results.get("response") is None
        or results["response"].get("offersGroup") is None
    ):
        return []

    for result in results["response"]["offersGroup"]:

        translated_result = {
            "api_name": "bdfare",
            "search_id": results["response"]["traceId"],
            "result_id": result["offer"]["offerId"],
            "is_refundable": result["offer"]["refundable"],
            "seats_available": result["offer"].get("seatsRemaining", 0),
            "total_fare": result["offer"]["price"]["totalPayable"]["total"],
            "validating_carrier": result["offer"]["validatingCarrier"],
            "segments": [],
            "fare_details": [],
            "baggage_details": [],
            "meta_data": search_params,
        }

        # Add the segments
        for segment in result["offer"]["paxSegmentList"]:
            translated_segment = {
                "origin": {
                    "airport_code": segment["paxSegment"]["departure"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["departure"]["terminalName"],
                    "departure_time": _iso_to_unix_local(
                        segment["paxSegment"]["departure"]["aircraftScheduledDateTime"]
                    ),
                },
                "destination": {
                    "airport_code": segment["paxSegment"]["arrival"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["arrival"]["terminalName"],
                    "arrival_time": _iso_to_unix_local(
                        segment["paxSegment"]["arrival"]["aircraftScheduledDateTime"]
                    ),
                },
                "airline": {
                    "airline_code": segment["paxSegment"]["operatingCarrierInfo"][
                        "carrierDesigCode"
                    ],
                    "airline_name": segment["paxSegment"]["operatingCarrierInfo"][
                        "carrierName"
                    ],
                    "flight_number": segment["paxSegment"]["flightNumber"],
                    "fare_basis": None,
                },
            }
            translated_result["segments"].append(translated_segment)

        # Add the fare details
        for fare_detail in result["offer"]["fareDetailList"]:
            translated_fare_detail = {
                "pax_type": fare_detail["fareDetail"]["paxType"],
                "pax_count": fare_detail["fareDetail"]["paxCount"],
                "currency": fare_detail["fareDetail"]["currency"],
                # ------ prices ------
                "base_price": fare_detail["fareDetail"]["baseFare"],
                "discount": fare_detail["fareDetail"]["discount"],
                "tax": (
                    fare_detail["fareDetail"]["tax"] + fare_detail["fareDetail"]["vat"]
                ),
                "other_charges": fare_detail["fareDetail"]["otherFee"],
                "sub_total_price": fare_detail["fareDetail"]["subTotal"],
            }
            translated_result["fare_details"].append(translated_fare_detail)

        # Add the baggage details
        for baggage_detail in result["offer"]["baggageAllowanceList"]:
            segment = f"{baggage_detail['baggageAllowance']['departure']} - {baggage_detail['baggageAllowance']['arrival']}"

            for index in range(len(baggage_detail["baggageAllowance"]["checkIn"])):
                translated_baggage = {
                    "segment": segment,
                    "check_in_weight": baggage_detail["baggageAllowance"]["checkIn"][
                        index
                    ]["allowance"],
                    "cabin_weight": baggage_detail["baggageAllowance"]["cabin"][index][
                        "allowance"
                    ],
                    "pax_type": baggage_detail["baggageAllowance"]["checkIn"][index][
                        "paxType"
                    ],
                }
                translated_result["baggage_details"].append(translated_baggage)

        translated_results.append(translated_result)

    return translated_results


def _iso_to_unix_local(iso_date_string):
    dt = datetime.fromisoformat(iso_date_string.rstrip("Z"))
    dt_utc = dt.replace(tzinfo=timezone.utc)  # UTC time
    unix_timestamp = dt_utc.timestamp()
    return int(unix_timestamp)


# ---------------------- Air Rules ----------------------


def air_rules_inject_translate(rules_params: dict):
    # translated to:
    """
    {
        "traceId": "cd0cd824-c...",
        "offerId": "cd0cd824-c...",
    }
    """

    return {
        "traceId": rules_params["search_id"],
        "offerId": rules_params["result_id"],
    }


def air_rules_result_translate(rules_params: dict):
    # translated to:
    """
    [
        {
            "city_route": "DAC - CXB",
            "rule_details": "description",
        }
    ]
    """

    translated_results = []
    print(rules_params)

    if rules_params["response"]["fareRuleRouteInfos"] is None:
        return []

    for rule in rules_params["response"]["fareRuleRouteInfos"]:
        translated_rule = {
            "city_route": rule["route"],
            "rule_details": [
                _format_fare_rules_to_string(rule) for rule in rule["fareRulePaxInfos"]
            ],
        }

        translated_results.append(translated_rule)

    return translated_results


def _format_fare_rules_to_string(fare_rules_dict):
    result = []

    result.append(fare_rules_dict["paxType"])
    result.append("")

    for fare_rule in fare_rules_dict["fareRuleInfos"]:
        result.append(fare_rule["category"])
        result.append(fare_rule["info"])
        result.append("")

    return "\n".join(result)


# ---------------------- Pricing Details ----------------------


def air_pricing_details_inject_translate(pricing_params: dict):
    # translated to:
    """
    {
        "traceId": "cd0cd824-c...",
        "offerId": "cd0cd824-c...",
    }
    """

    return {
        "traceId": pricing_params["search_id"],
        "offerId": [pricing_params["result_id"]],
    }


# ---------------------- Flight Booking ----------------------


def flight_booking_inject_translate(booking_params: dict):
    # translated to:
    """
    {
        "traceId": "cd0cd824-c6bd-4025-893c-ccf4577dd454",
        "offerId": [
            "string"
        ],
        "request": {
            "contactInfo": {
            "phone": {
                "phoneNumber": "1234567",
                "countryDialingCode": "880"
            },
            "emailAddress": "abc@xyz.com"
            },
            "paxList": [
                    {
                    "ptc": "Adult",
                    "individual": {
                    "givenName": "John",
                    "surname": "Wick",
                    "gender": "Male",
                    "birthdate": "1978-12-25",
                    "nationality": "BD",

                    // optional
                    "identityDoc": {
                        "identityDocType": "Passport",
                        "identityDocID": "BB458924",
                        "expiryDate": "2025-12-27"
                    },

                    // optional
                    "associatePax": {
                        "givenName": "John",
                        "surname": "Wick"
                        }
                    },

                    // optional
                    "sellSSR": [
                    {
                        "ssrRemark": "",
                        "ssrCode": "WCHR",
                        "loyaltyProgramAccount": {
                        "airlineDesigCode": "BS",
                        "accountNumber": "3523626235"
                        }
                    }
                    ]
                }
            ]
        }
    }
    """

    translated_booking_params = {
        "traceId": booking_params["search_id"],
        "offerId": [booking_params["result_id"]],
        "request": {
            "contactInfo": {
                "phone": {
                    "phoneNumber": booking_params["lead_passenger_info"][
                        "contact_number"
                    ],
                    "countryDialingCode": booking_params["lead_passenger_info"][
                        "country_dialing_code"
                    ],
                },
                "emailAddress": booking_params["lead_passenger_info"]["email"],
            },
            "paxList": [],
        },
    }

    pax_list = booking_params["other_passengers_info"] + [
        booking_params["lead_passenger_info"]
    ]

    for pax in pax_list:
        pax_info = {
            "ptc": pax["pax_type"],
            "individual": {
                "givenName": pax["first_name"],
                "surname": pax["last_name"],
                "gender": pax["gender"],
                "birthdate": pax["birth_date"],
                "nationality": pax["country_code"],
            },
        }
        if pax["passport_number"] != "":
            pax_info["individual"]["identityDoc"] = {
                "identityDocType": "Passport",
                "identityDocID": pax["passport_number"],
                "expiryDate": pax["passport_expiry_date"],
            }
        translated_booking_params["request"]["paxList"].append(pax_info)

    print(translated_booking_params)
    return translated_booking_params


def flight_pre_booking_result_translate(booking_params: dict, meta_data: dict):
    if (
        booking_params is None
        or booking_params.get("response") is None
        or booking_params["response"].get("offersGroup") is None
    ):
        return {"error": "Cannot process your request"}

    return search_result_translate(booking_params, meta_data)


def flight_booking_result_translate(booking_params: dict, meta_data: dict):
    # translated to:
    """
    [
        {
            api_name: "",
            search_id: "",
            result_id: "",
            is_refundable: False,
            seats_available: 1,
            fare_basis: [],
            total_fare: 1200,

            segments: [
            {
                origin: {
                    airport_code: "DAC",
                    terminal: "",
                    departure_time: "2024-07-20T11:45:00",
                },
                distination: {
                    airport_code: "DAC",
                    terminal: "",
                    arrival_time: "2024-07-20T11:45:00",
                },
                airline: {
                    airline_code: "UK",
                    airline_name: "Vistara",
                    flight_number: "184",
                },
            },
            ],

            fare_details: [
                {
                    "pax_type": "Adult",
                    "pax_count": 1,
                    "currency": "BDT",

                    "base_price": 5719,
                    "discount": 0,
                    "tax": 120,
                    "other_charges": 122,
                    "sub_total_price": 6727
                }
            ]

            baggage_details: [
                {
                    segment: "DAC - CXB",
                    check_in_weight: 20,
                    cabin_weight: 7,
                    pax_type: "Adult",
                }
            ]

            meta_data: search_params
        },
    ]
    """

    print(booking_params)

    translated_results = []

    if (
        booking_params is None
        or booking_params.get("response") is None
        or booking_params["response"].get("orderItem") is None
    ):
        return {"error": "Cannot process your request"}

    for result in booking_params["response"]["orderItem"]:

        translated_result = {
            "api_name": "bdfare",
            "search_id": booking_params["response"]["traceId"],
            "result_id": None,
            "is_refundable": result["refundable"],
            "seats_available": result.get("seatsRemaining", 0),
            "fare_basis": [],
            "total_fare": result["price"]["totalPayable"]["total"],
            "segments": [],
            "fare_details": [],
            "baggage_details": [],
            "meta_data": meta_data,
        }

        # Add the segments
        for segment in result["paxSegmentList"]:
            translated_segment = {
                "origin": {
                    "airport_code": segment["paxSegment"]["departure"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["departure"]["terminalName"],
                    "departure_time": _iso_to_unix_local(
                        segment["paxSegment"]["departure"]["aircraftScheduledDateTime"]
                    ),
                },
                "distination": {
                    "airport_code": segment["paxSegment"]["arrival"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["arrival"]["terminalName"],
                    "arrival_time": _iso_to_unix_local(
                        segment["paxSegment"]["arrival"]["aircraftScheduledDateTime"]
                    ),
                },
                "airline": {
                    "airline_code": segment["paxSegment"]["operatingCarrierInfo"][
                        "carrierDesigCode"
                    ],
                    "airline_name": segment["paxSegment"]["operatingCarrierInfo"][
                        "carrierName"
                    ],
                    "flight_number": segment["paxSegment"]["flightNumber"],
                },
            }
            translated_result["segments"].append(translated_segment)

        # Add the fare details
        for fare_detail in result["fareDetailList"]:
            translated_fare_detail = {
                "pax_type": fare_detail["fareDetail"]["paxType"],
                "pax_count": fare_detail["fareDetail"]["paxCount"],
                "currency": fare_detail["fareDetail"]["currency"],
                # ------ prices ------
                "base_price": fare_detail["fareDetail"]["baseFare"],
                "discount": fare_detail["fareDetail"]["discount"],
                "tax": (
                    fare_detail["fareDetail"]["tax"] + fare_detail["fareDetail"]["vat"]
                ),
                "other_charges": fare_detail["fareDetail"]["otherFee"],
                "sub_total_price": fare_detail["fareDetail"]["subTotal"],
            }
            translated_result["fare_details"].append(translated_fare_detail)

        # Add the baggage details
        for baggage_detail in result["baggageAllowanceList"]:
            segment = f"{baggage_detail['baggageAllowance']['departure']} - {baggage_detail['baggageAllowance']['arrival']}"

            for index in range(len(baggage_detail["baggageAllowance"]["checkIn"])):
                translated_baggage = {
                    "segment": segment,
                    "check_in_weight": baggage_detail["baggageAllowance"]["checkIn"][
                        index
                    ]["allowance"],
                    "cabin_weight": baggage_detail["baggageAllowance"]["cabin"][index][
                        "allowance"
                    ],
                    "pax_type": baggage_detail["baggageAllowance"]["checkIn"][index][
                        "paxType"
                    ],
                }
                translated_result["baggage_details"].append(translated_baggage)

        translated_results.append(translated_result)

    return translated_results


# import json
# x = json.load(open("response.json"))
# print(json.dumps(flight_booking_result_translate(x), indent=4))
