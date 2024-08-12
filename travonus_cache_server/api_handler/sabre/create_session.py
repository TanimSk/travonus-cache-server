from api_handler.utils import call_external_api
from api_handler.sabre import urls
from api_handler.models import SessionToken
from django.conf import settings
import xml.etree.ElementTree as ET


def xml_header(session_token: str) -> str:
    return f"""
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
    <SOAP-ENV:Header>
        <MessageHeader xmlns="http://www.ebxml.org/namespaces/messageHeader">
            <From>
                <PartyId>Agency</PartyId>
            </From>
            <To>
                <PartyId>SWS</PartyId>
            </To>
            <ConversationId>2019.09.DevStudio</ConversationId>
            <Action>OTA_AirRulesLLSRQ</Action>
        </MessageHeader>
        <Security xmlns="http://schemas.xmlsoap.org/ws/2002/12/secext">
            <BinarySecurityToken EncodingType="Base64Binary" valueType="String">
                {session_token}
            </BinarySecurityToken>
        </Security>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
    """


def xml_footer() -> str:
    return """
    </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """


def create_session():

    # xml body
    body = f"""
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
        <SOAP-ENV:Header>
            <MessageHeader xmlns="http://www.ebxml.org/namespaces/messageHeader">
                <From>
                    <PartyId>Agency</PartyId>
                </From>
                <To>
                    <PartyId>Sabre_API</PartyId>
                </To>
                <ConversationId>2021.01.DevStudio</ConversationId>
                <Action>SessionCreateRQ</Action>
            </MessageHeader>
            <Security xmlns="http://schemas.xmlsoap.org/ws/2002/12/secext">
                <UsernameToken>
                    <Username>{settings.SABRE_USERNAME}</Username>
                    <Password>{settings.SABRE_PASSWORD_SANDBOX}</Password>
                    <Organization>{settings.SABRE_PCC}</Organization>
                    <Domain>DEFAULT</Domain>
                </UsernameToken>
            </Security>
        </SOAP-ENV:Header>
        <SOAP-ENV:Body>
            <SessionCreateRQ returnContextID="true" Version="1.0.0" xmlns="http://www.opentravel.org/OTA/2002/11"/>
        </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """

    api_response = call_external_api(
        urls.XML_BASE_URL,
        method="POST",
        data=body,
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "SessionCreateRQ",
        },
        content="data",
        ssl=False,
    )

    session_token = extract_session_token(api_response)

    # Save the session token in the database
    if session_token is not None:
        SessionToken.objects.create(token=session_token)


def extract_session_token(xml_response):
    # Parse the XML response
    root = ET.fromstring(xml_response)

    # Define namespaces
    namespaces = {
        "soap-env": "http://schemas.xmlsoap.org/soap/envelope/",
        "eb": "http://www.ebxml.org/namespaces/messageHeader",
        "wsse": "http://schemas.xmlsoap.org/ws/2002/12/secext",
    }

    # Find the BinarySecurityToken element
    token_element = root.find(".//wsse:BinarySecurityToken", namespaces)

    # Extract and return the token text
    if token_element is not None:
        return token_element.text
    else:
        return None
