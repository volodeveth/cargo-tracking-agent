import re
from ..models.enums import NormalizedStatus as S

AIR_RULES = [
    (re.compile(r"deliver", re.I), S.DELIVERED),
    (re.compile(r"notif|ready for (pick|collect)|\bNFD\b", re.I), S.READY_FOR_PICKUP),
    (re.compile(r"customs", re.I), S.CUSTOMS),
    (re.compile(r"arriv|\bARR\b|\bRCF\b", re.I), S.ARRIVED),
    (re.compile(r"transit|\bMAN\b|transfer", re.I), S.IN_TRANSIT),
    (re.compile(r"depart|\bDEP\b", re.I), S.DEPARTED),
    (re.compile(r"accept|origin terminal", re.I), S.IN_ORIGIN_TERMINAL),
    (re.compile(r"received|\bRCS\b|cargo received", re.I), S.RECEIVED),
    (re.compile(r"book", re.I), S.BOOKED),
    (re.compile(r"creat", re.I), S.CREATED),
    (re.compile(r"exception|hold|fail|delay", re.I), S.EXCEPTION),
]
