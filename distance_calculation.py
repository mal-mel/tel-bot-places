from math import sin, asin, cos, sqrt, pi

EARTH_RADIUS = 6371.2


def calculate(lat1, lat2, lon1, lon2):
    lat1, lon1 = radian(lat1, lon1)
    lat2, lon2 = radian(lat2, lon2)
    sin_1 = sin((lat1 - lat2) / 2)
    sin_2 = sin((lon1 - lon2) / 2)
    return 2*EARTH_RADIUS*asin(sqrt(sin_1*sin_1+sin_2*sin_2*cos(lat1)*cos(lat2))) * 1000


def radian(lat, lon):
    radian_1 = (lat * pi) / 180
    radian_2 = (lon * pi) / 180
    return (radian_1, radian_2)

