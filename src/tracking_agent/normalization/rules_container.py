import re
from ..models.enums import NormalizedStatus as S

CONTAINER_RULES = [
    (re.compile(r"empty return|returned empty", re.I), S.CONTAINER_RETURNED),
    (re.compile(r"deliver", re.I), S.DELIVERED),
    (re.compile(r"available|ready for (pick|collect)", re.I), S.READY_FOR_PICKUP),
    (re.compile(r"customs", re.I), S.CUSTOMS),
    (re.compile(r"discharg|arriv", re.I), S.ARRIVED),
    (re.compile(r"loaded on vessel|vessel depart|transship|in transit", re.I), S.IN_TRANSIT),
    (re.compile(r"gate out empty|empty pickup|pick.?up empty", re.I), S.CONTAINER_PICKED_UP),
    (re.compile(r"gate in|received", re.I), S.RECEIVED),
    (re.compile(r"book", re.I), S.BOOKED),
    (re.compile(r"exception|hold|fail|delay", re.I), S.EXCEPTION),
]
