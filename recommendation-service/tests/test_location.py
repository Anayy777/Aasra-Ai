from app.location import haversine_distance


# Example: two locations in Delhi
user_lat = 28.6139
user_lon = 77.2090

course_lat = 28.6200
course_lon = 77.2150


distance = haversine_distance(
    user_lat,
    user_lon,
    course_lat,
    course_lon
)


print("Distance:", round(distance, 2), "km")

