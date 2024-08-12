from datetime import datetime
import time

##############
# Flyhub API #
##############


# ---------------------- Air Search ----------------------


def air_search_translate(search_params: dict):
    # translated to:
    """
    {
        "AdultQuantity": 1,
        "ChildQuantity": 0,
        "InfantQuantity": 0,
        "EndUserIp": "192.168.1.1",
        "JourneyType": "1",
        "Segments": [
            {
                "Origin": "DEL",
                "Destination": "DXB",
                "CabinClass": "1",
                "DepartureDateTime": "2018-12-04",
            }
        ],
    }
    """

    journey_type_map = {
        "Oneway": 1,
        "Return": 2,  # Round trip
        "Multicity": 3,
    }

    booking_class_map = {
        "Economy": 1,
        "Premium Economy": 2,
        "Business": 3,
        "First": 4,
    }

    translated_search_params = {
        "AdultQuantity": search_params["adult_quantity"],
        "ChildQuantity": search_params["child_quantity"],
        "InfantQuantity": search_params["infant_quantity"],
        "EndUserIp": search_params["user_ip"],
        "JourneyType": str(journey_type_map[search_params["journey_type"]]),
    }

    translated_search_params["Segments"] = []

    for segment in search_params["segments"]:

        translated_segment = {
            "Origin": segment["origin"],
            "Destination": segment["destination"],
            "CabinClass": str(booking_class_map[search_params["booking_class"]]),
            "DepartureDateTime": segment["departure_date"],
        }
        translated_search_params["Segments"].append(translated_segment)

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
                destination: {
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
            ],

            "meta_data": search_params,
        },
    ]
    """

    translated_results = []

    pax_type_map = {
        1: "Adult",
        2: "Child",
        3: "Infant",
    }

    if results is None or results.get("Results") is None:
        return translated_results

    for result in results.get("Results", []):
        translated_result = {
            "api_name": "flyhub",
            "search_id": results.get("SearchId"),
            "result_id": result["ResultID"],
            "is_refundable": result["IsRefundable"],
            "seats_available": result["Availabilty"],
            "total_fare": result["TotalFare"],
            "validating_carrier": result["Validatingcarrier"],
            "segments": [],
            "fare_details": [],
            "baggage_details": [],
            "meta_data": search_params,
        }

        # Add the segments
        for segment in result["segments"]:
            translated_segment = {
                "origin": {
                    "airport_code": segment["Origin"]["Airport"]["AirportCode"],
                    "terminal": segment["Origin"]["Airport"]["Terminal"],
                    "departure_time": iso_to_unix_local(segment["Origin"]["DepTime"]),
                },
                "destination": {
                    "airport_code": segment["Destination"]["Airport"]["AirportCode"],
                    "terminal": segment["Destination"]["Airport"]["Terminal"],
                    "arrival_time": iso_to_unix_local(
                        segment["Destination"]["ArrTime"]
                    ),
                },
                "airline": {
                    "airline_code": segment["Airline"]["AirlineCode"],
                    "airline_name": segment["Airline"]["AirlineName"],
                    "flight_number": segment["Airline"]["FlightNumber"],
                    "fare_basis": None,
                },
            }

            # Add baggage details
            for baggage_details in segment.get("baggageDetails", []):
                translated_baggage = {
                    "segment": f"{segment['Origin']['Airport']['AirportCode']} - {segment['Destination']['Airport']['AirportCode']}",
                    "check_in_weight": baggage_details["Checkin"],
                    "cabin_weight": baggage_details["Cabin"],
                    "pax_type": pax_type_map[baggage_details["PaxType"]],
                }
                translated_result["baggage_details"].append(translated_baggage)

            translated_result["segments"].append(translated_segment)

        # Add the fare details
        for fare_detail in result["Fares"]:
            translated_fare_detail = {
                "pax_type": fare_detail.get("paxType"),
                "pax_count": fare_detail["PassengerCount"],
                "currency": fare_detail["Currency"],
                # ------ prices ------
                "base_price": fare_detail["BaseFare"],
                "discount": fare_detail["Discount"],
                "tax": fare_detail["Tax"],
                "other_charges": (
                    fare_detail["OtherCharges"]
                    + fare_detail["ServiceFee"]
                    + fare_detail["AgentMarkUp"]
                ),
                "sub_total_price": fare_detail["BaseFare"]
                + fare_detail["Tax"]
                + fare_detail["OtherCharges"]
                + fare_detail["AgentMarkUp"]
                + fare_detail["ServiceFee"]
                - fare_detail["Discount"],
            }
            translated_result["fare_details"].append(translated_fare_detail)

        translated_results.append(translated_result)

    return translated_results


def iso_to_unix_local(iso_date_string):
    dt = datetime.fromisoformat(iso_date_string)
    # Convert the datetime object to a Unix timestamp (seconds since epoch)
    unix_timestamp = time.mktime(dt.timetuple())
    return int(unix_timestamp)


# ---------------------- Air Rules ----------------------


def air_rules_inject_translate(rules_params: dict):
    # translated to:
    """
    {
        "SearchID": "cd0cd824-c...",
        "ResultID": "cd0cd824-c...",
    }
    """

    return {
        "SearchID": rules_params["search_id"],
        "ResultID": rules_params["result_id"],
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

    if type(rules_params) is not list:
        if not rules_params.get("Error") == None:
            return rules_params["Error"]["ErrorMessage"]

    translated_results = []

    for rule in rules_params:
        translated_rule = {
            "city_route": rule["CityPair"],
            "rule_details": [f"{rule['Paxtype']}\n\n{rule['RuleDetails']}"],
        }

        translated_results.append(translated_rule)

    return translated_results


# ---------------------- Flight Booking ----------------------
def flight_booking_inject_translate(booking_params: dict):
    # translated to:
    """
    {
        "SearchID": "1b123aae-dd05-48e7-b12a-b14436595c50",
        "ResultID": "e80ee235-3a31-4435-a308-4bc8cdd50ec7",
        "Passengers": [
            {
                "Title": "Mr",
                "FirstName": "karim",
                "LastName": "ahmed",
                "PaxType": "Adult",
                "DateOfBirth": "1975-10-06",
                "Gender": "Male",
                "Address1": "test",
                "CountryCode": "BD",
                "Nationality": "BD",
                "ContactNumber": "577989789789",
                "Email": "test@m.com",
                "IsLeadPassenger": True,
            }
        ],
    }
    """

    translated_booking_params = {
        "SearchID": booking_params["search_id"],
        "ResultID": booking_params["result_id"],
        "Passengers": [
            {
                "Title": booking_params["lead_passenger_info"]["title"],
                "FirstName": booking_params["lead_passenger_info"]["first_name"],
                "LastName": booking_params["lead_passenger_info"]["last_name"],
                "PaxType": booking_params["lead_passenger_info"]["pax_type"],
                "DateOfBirth": booking_params["lead_passenger_info"]["birth_date"],
                "Gender": booking_params["lead_passenger_info"]["gender"],
                "Address1": booking_params["lead_passenger_info"]["address_1"],
                "Address2": booking_params["lead_passenger_info"]["address_2"],
                "CountryCode": booking_params["lead_passenger_info"]["country_code"],
                "Nationality": booking_params["lead_passenger_info"]["nationality"],
                "ContactNumber": booking_params["lead_passenger_info"][
                    "contact_number"
                ],
                "Email": booking_params["lead_passenger_info"]["email"],
                "IsLeadPassenger": True,
                # Passport Info
                "PassportNumber": booking_params["lead_passenger_info"].get(
                    "passport_number"
                ),
                "PassportExpiryDate": booking_params["lead_passenger_info"].get(
                    "passport_expiry_date"
                ),
                "PassportNationality": booking_params["lead_passenger_info"].get(
                    "passport_nationality"
                ),
            },
        ],
    }

    for other_passenger in booking_params["other_passengers_info"]:
        translated_passenger = {
            "Title": other_passenger["title"],
            "FirstName": other_passenger["first_name"],
            "LastName": other_passenger["last_name"],
            "PaxType": other_passenger["pax_type"],
            "DateOfBirth": other_passenger["birth_date"],
            "Gender": other_passenger["gender"],
            "Address1": other_passenger["address_1"],
            "Address2": other_passenger["address_2"],
            "CountryCode": other_passenger["country_code"],
            "Nationality": other_passenger["nationality"],
            "ContactNumber": other_passenger["contact_number"],
            "Email": other_passenger["email"],
            "IsLeadPassenger": False,
            # Passport Info
            "PassportNumber": other_passenger.get("passport_number"),
            "PassportExpiryDate": other_passenger.get("passport_expiry_date"),
            "PassportNationality": other_passenger.get("passport_nationality"),
        }
        translated_booking_params["Passengers"].append(translated_passenger)

    return translated_booking_params


def flight_pre_booking_result_translate(booking_params: dict, meta_data: dict):
    if not booking_params.get("Error") == None:
        return {
            "error": booking_params["Error"]["ErrorMessage"],
        }

    return search_result_translate(booking_params, meta_data)


def flight_booking_result_translate(booking_params: dict, meta_data: dict):
    if not booking_params.get("Error") == None:
        return {
            "error": booking_params["Error"]["ErrorMessage"],
        }

    return search_result_translate(booking_params, meta_data)


def flight_ticket_inject_translate(ticket_params: dict) -> dict:
    """
    {
        "BookingID": "..."
        "IsAcceptedPriceChangeandIssueTicket": "True"
    }
    """

    return {
        "BookingID": ticket_params["booking_id"],
        "IsAcceptedPriceChangeandIssueTicket": "True",
    }
