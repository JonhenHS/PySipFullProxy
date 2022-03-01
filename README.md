<h1>SIP Proxy</h1>
<h2>Source</h2>
Assignment 1 for MTAA.
Original library was forked from <a href="https://github.com/tirfil/PySipFullProxy">here</a> and modified to fit 
my needs.

<h2>Required Functionalities</h2>

Required captures which document can be found in the "pcaps" folder. All required functionalities were successfully 
implemented.

<ul>
    <li> User Registration </li>
    <li> Call dialing and ringing </li>
    <li> Call answering and its normal operation </li>
    <li> Call ending / denial </li>
</ul>

<h2> Optional functionalities </h2>

<ul>
    <li> Conference call (at least 3 attendees) </li>
    <li> Call transfer </li>
    <li> Video call </li>
    <li> Logs </li>
    <li> Status codes replacement </li>
</ul>

While first 3 optionals were fully implemented the other 2 were implemented only partially.

Logs are being written for every message sent to sip.log file. It contains more than only calls information however
this can be extracted.

SIP status codes are included in codes.json file. While everything originating from the proxy itself can be easily modified,
messages sent from other devices are created using their predefined codes. 
This could be modified while forwarding, but it would require parsing every sent datagram, matching and replacing every
original status code. This didn't seem like a good idea on a real-time data.

