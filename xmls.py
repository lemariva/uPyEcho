# This XML is the minimum needed to define one of our virtual switches
# to the Amazon Echo Dot / Amazon Echo (2nd generation)

SETUP_XML = """<?xml version="1.0"?>
<root>
  <device>
    <deviceType>urn:LeMaRiva:device:controllee:1</deviceType>
    <friendlyName>%(device_name)s</friendlyName>
    <manufacturer>Belkin International Inc.</manufacturer>
    <modelName>Emulated Socket</modelName>
    <modelNumber>3.1415</modelNumber>
    <UDN>uuid:Socket-1_0-%(device_serial)s</UDN>
    <serialNumber>221517K0101769</serialNumber>
    <binaryState>0</binaryState>
    <serviceList>
      <service>
          <serviceType>urn:Belkin:service:basicevent:1</serviceType>
          <serviceId>urn:Belkin:serviceId:basicevent1</serviceId>
          <controlURL>/upnp/control/basicevent1</controlURL>
          <eventSubURL>/upnp/event/basicevent1</eventSubURL>
          <SCPDURL>/eventservice.xml</SCPDURL>
      </service>
    </serviceList>
  </device>
</root>
"""

EVENT_SERVICE_XML = """<?scpd xmlns="urn:Belkin:service-1-0"?>
<actionList>
  <action>
    <name>SetBinaryState</name>
    <argumentList>
      <argument>
        <retval/>
        <name>BinaryState</name>
        <relatedStateVariable>BinaryState</relatedStateVariable>
        <direction>in</direction>
      </argument>
    </argumentList>
     <serviceStateTable>
      <stateVariable sendEvents="yes">
        <name>BinaryState</name>
        <dataType>Boolean</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
      <stateVariable sendEvents="yes">
        <name>level</name>
        <dataType>string</dataType>
        <defaultValue>0</defaultValue>
      </stateVariable>
    </serviceStateTable>
  </action>
</scpd>
"""

GET_BINARY_STATE_SOAP = """<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetBinaryStateResponse xmlns:u="urn:Belkin:service:basicevent:1">
      <BinaryState>%(state_realy)s</BinaryState>
    </u:GetBinaryStateResponse>
  </s:Body>
</s:Envelope>
"""