from datetime import datetime, timezone, timedelta
from dateutil import parser
from decimal import Decimal
from api_handler.constants import IATA_AIRPORT_CODE_MAP, AIRPORT_TO_GMT
from django.db.models import QuerySet
from api_handler.utils import get_total_fare_with_markup


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
                "preferCombine": True,
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


def process_search_result(
    results: dict,
    search_params: dict,
    trace_id: str = None,
    admin_markup: Decimal = None,
    agent_markup_instance=None,
):
    # validation
    if (
        results is None
        or results.get("response") is None
        or (
            (
                (
                    type(results["response"].get("offersGroup")) is list
                    and len(results["response"]["offersGroup"]) == 0
                )
                or results["response"].get("offersGroup") is None
            )
            and (
                (
                    type(results["response"].get("specialReturnOffersGroup")) is list
                    and len(results["response"]["specialReturnOffersGroup"]) == 0
                )
                or results["response"].get("specialReturnOffersGroup") is None
            )
        )
    ):
        return []

    return search_result_translate(
        results=results["response"]["offersGroup"],
        search_params=search_params,
        search_id=results["response"]["traceId"],
        trace_id=trace_id,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )


def search_result_translate(
    results: list,
    search_params: dict,
    direction: str = None,
    search_id: str = None,
    trace_id: str = None,
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

            only_admin_markup: 50,
            only_agent_markup: 50,
            base_price: 1100,
            price_with_admin_markup: 1150,
            total_fare: 1200,

            "first_departure_time": 0,
            "final_arrival_time": 0,
            duration: 2423,
            inbound_stops: 0,
            outbound_stops: 0,

            validating_carrier: "UK",
            airlines: ["UK", "BG"],

            segments: [
            {
                // added
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

            cancellation: {}
            date_change: {}

            meta_data: search_params
        },
    ]
    """

    translated_results = []

    for result in results:

        # filtering with preferred airlines
        if search_params.get("preferred_airlines") is not None:
            if (
                result["offer"]["validatingCarrier"]
                not in search_params["preferred_airlines"]
            ):
                continue

        # filtering with refundable flights
        if search_params.get("refundable") is not None:
            if result["offer"]["refundable"] != search_params["refundable"]:
                continue

        raw_price = Decimal(str(result["offer"]["price"]["totalPayable"]["total"]))
        total_fare_with_markup = get_total_fare_with_markup(
            raw_price=raw_price,
            admin_markup_percentage=admin_markup,
            agent_markup_instance=agent_markup_instance,
        )

        translated_result = {
            "trace_id": trace_id,
            "api_name": "bdfare",
            "search_id": search_id,
            "result_id": result["offer"]["offerId"],
            "is_refundable": result["offer"]["refundable"],
            "seats_available": result["offer"].get("seatsRemaining", 0),
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
            "inbound_stops": 0,
            "outbound_stops": 0,
            "validating_carrier": result["offer"]["validatingCarrier"],
            "airlines": set(),
            "segments": [],
            "fare_details": [],
            "baggage_details": [],
            "meta_data": search_params,
        }

        # Add the first departure time
        translated_result["first_departure_time"] = _iso_to_unix_local(
            iso_date_string=result["offer"]["paxSegmentList"][0]["paxSegment"][
                "departure"
            ]["aircraftScheduledDateTime"],
            iata_code=result["offer"]["paxSegmentList"][0]["paxSegment"]["departure"][
                "iatA_LocationCode"
            ],
            gmt_offset=search_params["gmt_offset"],
            only_time=True,
        )["only_time"]

        # Add the segments
        for segment in result["offer"]["paxSegmentList"]:

            # timing
            departure_time = _iso_to_unix_local(
                iso_date_string=segment["paxSegment"]["departure"][
                    "aircraftScheduledDateTime"
                ],
                iata_code=segment["paxSegment"]["departure"]["iatA_LocationCode"],
                gmt_offset=search_params["gmt_offset"],
            )
            arrival_time = _iso_to_unix_local(
                iso_date_string=segment["paxSegment"]["arrival"][
                    "aircraftScheduledDateTime"
                ],
                iata_code=segment["paxSegment"]["arrival"]["iatA_LocationCode"],
                gmt_offset=search_params["gmt_offset"],
            )

            translated_segment = {
                "direction": (
                    "inbound"
                    if segment["paxSegment"]["returnJourney"]
                    else ("outbound" if not direction else direction)
                ),
                "origin": {
                    "airport_code": segment["paxSegment"]["departure"][
                        "iatA_LocationCode"
                    ],
                    "full_name": IATA_AIRPORT_CODE_MAP.get(
                        segment["paxSegment"]["departure"]["iatA_LocationCode"]
                    ),
                    "terminal": segment["paxSegment"]["departure"]["terminalName"],
                    "departure_time": departure_time["unix_time"],
                    "gmt_offset_seconds": departure_time["gmt_offset_seconds"],
                },
                "technical_stops": [],
                "destination": {
                    "airport_code": segment["paxSegment"]["arrival"][
                        "iatA_LocationCode"
                    ],
                    "full_name": IATA_AIRPORT_CODE_MAP.get(
                        segment["paxSegment"]["arrival"]["iatA_LocationCode"]
                    ),
                    "terminal": segment["paxSegment"]["arrival"]["terminalName"],
                    "arrival_time": arrival_time["unix_time"],
                    "gmt_offset_seconds": arrival_time["gmt_offset_seconds"],
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

            # Add the technical stops
            if segment["paxSegment"]["technicalStopOver"] is not None:
                for technical_stop in segment["paxSegment"]["technicalStopOver"]:
                    technical_stop_arrival_time = _iso_to_unix_local(
                        iso_date_string=technical_stop[
                            "aircraftScheduledArrivalDateTime"
                        ],
                        iata_code=technical_stop["iatA_LocationCode"],
                        gmt_offset=search_params["gmt_offset"],
                    )
                    technical_stop_departure_time = _iso_to_unix_local(
                        iso_date_string=technical_stop[
                            "aircraftScheduledDepartureDateTime"
                        ],
                        iata_code=technical_stop["iatA_LocationCode"],
                        gmt_offset=search_params["gmt_offset"],
                    )

                    translated_technical_stop = {
                        "airport_code": technical_stop["iatA_LocationCode"],
                        "full_name": IATA_AIRPORT_CODE_MAP.get(
                            technical_stop["iatA_LocationCode"],
                            technical_stop["iatA_LocationCode"],
                        ),
                        "arrival_time": technical_stop_arrival_time["unix_time"],
                        "departure_time": technical_stop_departure_time["unix_time"],
                        "gmt_offset_seconds": technical_stop_arrival_time[
                            "gmt_offset_seconds"
                        ],
                    }
                translated_segment["technical_stops"].append(translated_technical_stop)
                # print(translated_segment["technical_stops"])

            translated_result["segments"].append(translated_segment)

            # Add the airline to the list
            translated_result["airlines"].add(
                segment["paxSegment"]["operatingCarrierInfo"]["carrierDesigCode"]
            )

            # update final_arrival_time
            translated_result["final_arrival_time"] = _iso_to_unix_local(
                iso_date_string=segment["paxSegment"]["arrival"][
                    "aircraftScheduledDateTime"
                ],
                iata_code=segment["paxSegment"]["arrival"]["iatA_LocationCode"],
                gmt_offset=search_params["gmt_offset"],
                only_time=True,
            )["only_time"]

            # update stops
            translated_result["inbound_stops"] += (
                1 if translated_segment["direction"] == "inbound" else 0
            )
            translated_result["outbound_stops"] += (
                1 if translated_segment["direction"] == "outbound" else 0
            )

        # check flight is return or not
        segment_length = int(
            len(translated_result["meta_data"]["segments"])
            if not search_params["journey_type"] == "Return"
            else len(search_params["segments"]) / 2
        )

        # modify stops
        if translated_result["outbound_stops"] > 0:
            translated_result["outbound_stops"] = (
                translated_result["outbound_stops"] - segment_length
            )

        if translated_result["inbound_stops"] > 0:
            translated_result["inbound_stops"] = (
                translated_result["inbound_stops"] - segment_length
            )

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

        # last arrival time - first departure time
        translated_result["duration"] = (
            translated_result["segments"][-1]["destination"]["arrival_time"]
            - translated_result["segments"][0]["origin"]["departure_time"]
        )

        # convert airlines set to list
        translated_result["airlines"] = list(translated_result["airlines"])

        translated_results.append(translated_result)

    return translated_results


# ---------------------- Air Rules ----------------------
def air_rules_mini_inject_translate(rules_params: dict) -> dict:
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


def air_rules_mini_result_translate(rules_params: dict):

    # translated from:
    """
    "response": {
        "penalty": {
            "refundPenaltyList": [
                {
                    "refundPenalty": {
                        "departure": "RJH",
                        "arrival": "DAC",
                        "penaltyInfoList": [
                            {
                                "penaltyInfo": {
                                    "type": "Before Departure",
                                    "textInfoList": [
                                        {
                                            "textInfo": {
                                                "paxType": "Adult",
                                                "info": [
                                                    "BDT 2030"
                                                ]
                                            }
                                        },
                                        {
                                            "textInfo": {
                                                "paxType": "Child",
                                                "info": [
                                                    "BDT 2030"
                                                ]
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "penaltyInfo": {
                                    "type": "After Departure",
                                    "textInfoList": [
                                        {
                                            "textInfo": {
                                                "paxType": "Adult",
                                                "info": [
                                                    "Cancellation allowed with fees"
                                                ]
                                            }
                                        },
                                        {
                                            "textInfo": {
                                                "paxType": "Child",
                                                "info": [
                                                    "Cancellation allowed with fees"
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ],
            "exchangePenaltyList": [
                {
                    "exchangePenalty": {
                        "departure": "RJH",
                        "arrival": "DAC",
                        "penaltyInfoList": [
                            {
                                "penaltyInfo": {
                                    "type": "Before Departure",
                                    "textInfoList": [
                                        {
                                            "textInfo": {
                                                "paxType": "Adult",
                                                "info": [
                                                    "BDT 2050"
                                                ]
                                            }
                                        },
                                        {
                                            "textInfo": {
                                                "paxType": "Child",
                                                "info": [
                                                    "BDT 2050"
                                                ]
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "penaltyInfo": {
                                    "type": "After Departure",
                                    "textInfoList": [
                                        {
                                            "textInfo": {
                                                "paxType": "Adult",
                                                "info": [
                                                    "Exchange allowed with fees"
                                                ]
                                            }
                                        },
                                        {
                                            "textInfo": {
                                                "paxType": "Child",
                                                "info": [
                                                    "Exchange allowed with fees"
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    },
    """

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

    translated_results = {
        "cancellation": [],
        "date_change": [],
    }

    for rule_type in [
        ["refundPenaltyList", "refundPenalty"],
        ["exchangePenaltyList", "exchangePenalty"],
    ]:
        # iterate over refund and exchange
        penalty_obj = rules_params["response"]["penalty"][rule_type[0]][0]
        city_pair = f"{penalty_obj[rule_type[1]]['departure']} - {penalty_obj[rule_type[1]]['arrival']}"

        # iterate over penaltyInfoList
        for penalty_info in penalty_obj[rule_type[1]]["penaltyInfoList"]:
            schedule_type = penalty_info["penaltyInfo"]["type"]

            # iterate over textInfoList
            for text_info in penalty_info["penaltyInfo"]["textInfoList"]:
                translated_rule = {
                    "pax_type": text_info["textInfo"]["paxType"],
                    "city_pair": city_pair,
                    "type": schedule_type,
                    "info": text_info["textInfo"]["info"][0],
                }

                if rule_type[0] == "refundPenaltyList":
                    translated_results["cancellation"].append(translated_rule)
                else:
                    translated_results["date_change"].append(translated_rule)

    return translated_results


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
    # print(rules_params)

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

    # print(translated_booking_params)
    return translated_booking_params


def flight_pre_booking_result_translate(
    booking_params: dict,
    meta_data: dict,
    admin_markup: Decimal,
    agent_markup_instance,
):
    if (
        booking_params is None
        or booking_params.get("response") is None
        or booking_params["response"].get("offersGroup") is None
    ):
        return {
            "__error": "You cannot pre-book this flight. Please try another flight."
        }

    result = process_search_result(
        results=booking_params,
        search_params=meta_data,
        trace_id=None,
        admin_markup=admin_markup,
        agent_markup_instance=agent_markup_instance,
    )
    if result is []:
        return {
            "__error": "You cannot pre-book this flight. Please try another flight."
        }

    return result


def flight_booking_result_translate(
    booking_params: dict,
    meta_data: dict,
    admin_markup: Decimal,
    agent_markup_instance,
):
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

            only_admin_markup: 50,
            only_agent_markup: 50,
            base_price: 1100,
            price_with_admin_markup: 1150,
            total_fare: 1200,


            pnr: "ABC123",

            segments: [
            {
                origin: {
                    airport_code: "DAC",
                    terminal: "",
                    departure_time: "2024-07-20T11:45:00",
                },
                destination: {
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

    # print(booking_params)

    translated_results = []

    if (
        booking_params is None
        or booking_params.get("response") is None
        or booking_params["response"].get("orderItem") is None
    ):
        return {"error": "Cannot process your request"}

    for result in booking_params["response"]["orderItem"]:

        # Calculate the total fare
        raw_price = Decimal(str(result["price"]["totalPayable"]["total"]))
        total_fare_with_markup = get_total_fare_with_markup(
            raw_price=raw_price,
            admin_markup_percentage=admin_markup,
            agent_markup_instance=agent_markup_instance,
        )

        translated_result = {
            "api_name": "bdfare",
            "search_id": booking_params["response"]["traceId"],
            "result_id": None,
            "is_refundable": result["refundable"],
            "seats_available": result.get("seatsRemaining", 0),
            "fare_basis": [],
            # markups
            "only_admin_markup": float(total_fare_with_markup["only_admin_markup"]),
            "only_agent_markup": float(total_fare_with_markup["only_agent_markup"]),
            # pricing details
            "base_price": float(raw_price),
            "price_with_admin_markup": float(
                total_fare_with_markup["price_with_admin_markup"]
            ),
            "total_fare": float(total_fare_with_markup["price_with_agent_markup"]),
            "segments": [],
            "fare_details": [],
            "baggage_details": [],
            "meta_data": meta_data,
            "pnr": result["paxSegmentList"][0]["paxSegment"]["airlinePNR"],
        }

        # Add the segments
        for segment in result["paxSegmentList"]:
            # timings
            departure_time = _iso_to_unix_local(
                iso_date_string=segment["paxSegment"]["departure"][
                    "aircraftScheduledDateTime"
                ],
                iata_code=segment["paxSegment"]["departure"]["iatA_LocationCode"],
                gmt_offset=meta_data["gmt_offset"],
            )
            arrival_time = _iso_to_unix_local(
                iso_date_string=segment["paxSegment"]["arrival"][
                    "aircraftScheduledDateTime"
                ],
                iata_code=segment["paxSegment"]["arrival"]["iatA_LocationCode"],
                gmt_offset=meta_data["gmt_offset"],
            )

            translated_segment = {
                "origin": {
                    "airport_code": segment["paxSegment"]["departure"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["departure"]["terminalName"],
                    "departure_time": departure_time["unix_time"],
                    "gmt_offset_seconds": departure_time["gmt_offset_seconds"],
                },
                "destination": {
                    "airport_code": segment["paxSegment"]["arrival"][
                        "iatA_LocationCode"
                    ],
                    "terminal": segment["paxSegment"]["arrival"]["terminalName"],
                    "arrival_time": arrival_time["unix_time"],
                    "gmt_offset_seconds": arrival_time["gmt_offset_seconds"],
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
# x = json.load(open("response_logs.json"))
# print(json.dumps(flight_booking_result_translate(x), indent=4))


def _iso_to_unix_local(
    iso_date_string, iata_code="", gmt_offset="+00:00", only_time=False
) -> dict:
    """
    Input: "2024-07-20T11:45:00+05:00", "+05:00"
    Returns: Unix timestamp as an integer.
    """

    # 1. Parse the ISO date string as a naive datetime (no timezone applied)
    gmt_offset = AIRPORT_TO_GMT.get(iata_code, gmt_offset)
    # convert "2024-07-20T11:45:00Z" to "2024-07-20T11:45:00+00:00"
    if iso_date_string[-1] == "Z":
        iso_date_string = iso_date_string.replace("Z", gmt_offset)
    else:
        iso_date_string += gmt_offset

    datetime_obj = parser.isoparse(iso_date_string)
    user_timezone = timezone(
        timedelta(
            hours=(
                int(gmt_offset[1:3]) if gmt_offset[0] == "+" else -int(gmt_offset[1:3])
            )
        )
    )

    datetime_user = datetime_obj.astimezone(user_timezone)

    if only_time:
        # Extract the time and calculate seconds since midnight
        midnight = datetime_user.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_since_midnight = (datetime_user - midnight).seconds
        return {
            "only_time": seconds_since_midnight,
        }

    unix_time = int(datetime_user.timestamp())
    return {
        "unix_time": unix_time,
        "gmt_offset_seconds": int(datetime_obj.utcoffset().total_seconds()),
    }
