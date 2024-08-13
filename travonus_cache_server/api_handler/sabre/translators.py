from datetime import datetime, timezone
from dateutil import parser
import time
import json
import xml.etree.ElementTree as ET
from api_handler.sabre import create_session
from api_handler.models import SessionToken
#########
# Sabre #
#########


# -------------------- Air search --------------------


def _return_quantity_dict(search_params: dict):
    passenger_type_array = []

    if search_params["adult_quantity"] > 0:
        passenger_type_array.append(
            {"Code": "ADT", "Quantity": search_params["adult_quantity"]}
        )
    if search_params["child_quantity"] > 0:
        passenger_type_array.append(
            {
                "Code": f"C{str(search_params['child_age']).zfill(2)}",
                "Quantity": search_params["child_quantity"],
            }
        )
    if search_params["infant_quantity"] > 0:
        passenger_type_array.append(
            {"Code": "INF", "Quantity": search_params["infant_quantity"]}
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
                                "Quantity": 1
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
        "Multicity": "OpenJaw",
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
    # print(json.dumps(results, indent=4))

    if (
        results is None
        or results.get("groupedItineraryResponse")["statistics"]["itineraryCount"] == 0
    ):
        return []

    for result in results["groupedItineraryResponse"]["itineraryGroups"][0][  # rethink
        "itineraries"
    ]:

        translated_result = {
            "api_name": "sabre",
            "search_id": None,
            "result_id": None,
            "is_refundable": not result["pricingInformation"][0]["fare"][  # rethink
                "passengerInfoList"
            ][0]["passengerInfo"]["nonRefundable"],
            # Available seats
            "seats_available": min(
                segment["segment"]["seatsAvailable"]
                for pricing in result["pricingInformation"]
                for passenger_info in pricing["fare"]["passengerInfoList"]
                for component in passenger_info["passengerInfo"]["fareComponents"]
                for segment in component["segments"]
            ),
            "total_fare": result["pricingInformation"][0]["fare"]["totalFare"][
                "totalPrice"
            ],
            "fare_details": [],
            "baggage_details": [],
            "validating_carrier": result["pricingInformation"][0]["fare"][
                "validatingCarrierCode"
            ],
            "segments": [],
            "meta_data": search_params,
        }

        fare_basis = []
        booking_codes = []

        # ----------- Add the fare details, fare basises, booking codes -----------
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

            # Adding fare basis and booking codes
            for fare_component in fare_details["passengerInfo"]["fareComponents"]:
                fare_basis.append(
                    extract_search_result_ref_obj(
                        results["groupedItineraryResponse"]["fareComponentDescs"],
                        fare_component["ref"],
                    ).get("fareBasisCode")
                )

                # add booking codes
                for segment in fare_component["segments"]:
                    booking_codes.append(segment["segment"]["bookingCode"])

        # ----------- Add the segments -----------
        segments_ids = []  # [{ref: 1, leg_index: 0}, {ref: 2, leg_index: 1}, ...]

        for index, leg in enumerate(result["legs"]):
            sub_segments = extract_search_result_ref_obj(
                target=results["groupedItineraryResponse"]["legDescs"],
                ref=leg["ref"],
            ).get("schedules")

            segments_ids.extend([{**data, "leg_index": index} for data in sub_segments])

        legs = results["groupedItineraryResponse"]["itineraryGroups"][0][
            "groupDescription"
        ][
            "legDescriptions"
        ]  # rethink

        for index, segment in enumerate(segments_ids):

            segment_description = extract_search_result_ref_obj(
                results["groupedItineraryResponse"]["scheduleDescs"], segment["ref"]
            )

            translated_segment = {
                "origin": {
                    "airport_code": segment_description["departure"]["city"],
                    "terminal": segment_description["arrival"].get("terminal"),
                    "departure_time": _iso_to_unix_local(
                        f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["departure"]["time"]}'
                    ),
                },
                "destination": {
                    "airport_code": segment_description["arrival"]["city"],
                    "terminal": segment_description["arrival"].get("terminal"),
                    "arrival_time": _iso_to_unix_local(
                        f'{legs[segment["leg_index"]]["departureDate"]}T{segment_description["arrival"]["time"]}'
                    ),
                },
                "airline": {
                    "validating_flight_number": segment_description["carrier"][
                        "marketingFlightNumber"
                    ],
                    "airline_code": segment_description["carrier"]["equipment"]["code"],
                    "airline_name": segment_description["carrier"]["operating"],
                    "flight_number": segment_description["carrier"][
                        "operatingFlightNumber"
                    ],
                    "fare_basis": (
                        fare_basis[index] if index < len(fare_basis) else None
                    ),
                    "booking_code": booking_codes[index],
                },
            }
            translated_result["segments"].append(translated_segment)

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

    for index, segment in enumerate(pricing_params["meta_data"]["segments"]):
        translated_segment = {
            "RPH": str(index + 1),
            "DepartureDateTime": segment["departure_date"] + "T00:00:00",
            "OriginLocation": {"LocationCode": segment["origin"]},
            "DestinationLocation": {"LocationCode": segment["destination"]},
            "TPA_Extensions": {
                "SegmentType": {"Code": "O"},
                # TODO: rethink here, there could be more segments
                "Flight": [
                    {
                        "Number": pricing_params["segments"][index]["airline"][
                            "flight_number"
                        ],
                        "DepartureDateTime": _unix_to_iso_date(
                            pricing_params["segments"][index]["origin"][
                                "departure_time"
                            ]
                        )
                        + "T00:00:00",
                        "ArrivalDateTime": _unix_to_iso_date(
                            pricing_params["segments"][index]["destination"][
                                "arrival_time"
                            ]
                        )
                        + "T00:00:00",
                        "Type": "A",
                        "ClassOfService": "K",
                        "OriginLocation": {
                            "LocationCode": pricing_params["segments"][index]["origin"][
                                "airport_code"
                            ]
                        },
                        "DestinationLocation": {
                            "LocationCode": pricing_params["segments"][index][
                                "destination"
                            ]["airport_code"]
                        },
                        "Airline": {
                            "Operating": pricing_params["segments"][index]["airline"][
                                "airline_name"
                            ],
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


# x = json.load(open("response.json"))
# print(json.dumps(search_result_translate(x), indent=4))


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
                "EndTransaction": {
                    "Source": {
                        "ReceivedFrom": "API"
                    }
                }
            }
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
                "OriginDestinationInformation": {
                    "FlightSegment": [],
                }
            },
            "PostProcessing": {
                "EndTransaction": {
                    "Source": {
                        "ReceivedFrom": "API",
                    }
                }
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
    for index, passenger in enumerate(all_pax):
        # add emails
        translated_booking_params["CreatePassengerNameRecordRQ"][
            "TravelItineraryAddInfo"
        ]["CustomerInfo"]["Email"].append(
            {
                "NameNumber": f"{index + 1}.1",
                "Address": passenger["email"],
                "Type": "CC",
            }
        )

        # add names
        translated_booking_params["CreatePassengerNameRecordRQ"][
            "TravelItineraryAddInfo"
        ]["CustomerInfo"]["PersonName"].append(
            {
                "NameNumber": f"{index + 1}.1",
                "GivenName": passenger["first_name"],
                "Surname": passenger["last_name"],
                "Infant": passenger["pax_type"] == "Infant",
                "NameReference": "",
                "PassengerType": (
                    pax_type_map[passenger["pax_type"]]
                    if not passenger["pax_type"] == "Child"
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
                ),
                "ArrivalDateTime": _unix_to_iso_datetime(
                    segment["destination"]["arrival_time"]
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
                "DestinationLocation": {
                    "LocationCode": segment["destination"]["airport_code"]
                },
                "MarketingAirline": {
                    "Code": booking_params["flight_ref"]["validating_carrier"],
                    "FlightNumber": str(segment["airline"]["validating_flight_number"]),
                },
            }
        )

    return translated_booking_params


def flight_booking_result_translate(booking_params: dict):
    return [booking_params["flight_ref"]]


def _iso_to_unix_local(full_time_string):
    # output: 1626163200

    datetime_obj = parser.isoparse(full_time_string)
    unix_time = int(datetime_obj.timestamp())

    return unix_time


def _unix_to_iso_date(unix_time):
    # output: 2023-09-20
    return datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%d")


def _unix_to_iso_datetime(unix_time):
    # output: 2023-09-20T12:35:00
    return datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%dT%H:%M:%S")
