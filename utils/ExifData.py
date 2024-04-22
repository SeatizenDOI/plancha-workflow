import cv2
import numpy as np
import pyexiv2


def restoreOrientation(image, orientation):
    if orientation == 8:
        restored_image = rotate(image, -90)
    elif orientation == 6:
        restored_image = rotate(image, 90)
    elif orientation == 3:
        restored_image = rotate(image, 180)
    else:
        restored_image = image

    return restored_image

def rotate(image, angle):
    # https://www.pyimagesearch.com/2017/01/02/rotate-images-correctly-with-opencv-and-python/

    height = image.shape[0]
    width = image.shape[1]
    center = (width/2, height/2)

    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    rotation_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    abs_cos = abs(rotation_mat[0, 0])
    abs_sin = abs(rotation_mat[0, 1])

    # compute the new bounding dimensions of the image
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)

    # adjust the rotation matrix to take into account translation
    rotation_mat[0, 2] += bound_w / 2 - center[0]
    rotation_mat[1, 2] += bound_h / 2 - center[1]

    # perform the actual rotation and return the image
    rotated_mat = cv2.warpAffine(image, rotation_mat, (bound_w, bound_h))
    return rotated_mat

def get_metadata(input_file):
    img = pyexiv2.Image(input_file)

    exif = img.read_exif()
    xmp = img.read_xmp()
    # print(exif)
    # print(xmp)

    focal_length = convert_string_to_float(exif['Exif.Photo.FocalLength']) / 1000    # unit: m
    # DEbug
    #orientation = int(exif['Exif.Image.Orientation'])
    orientation = 1
    #maker = exif["Exif.Image.Make"]
    maker = "plancha"

    longitude = convert_dms_to_deg(exif["Exif.GPSInfo.GPSLongitude"])
    latitude = convert_dms_to_deg(exif["Exif.GPSInfo.GPSLatitude"])

    lon_ref = exif['Exif.GPSInfo.GPSLongitudeRef']
    lat_ref = exif['Exif.GPSInfo.GPSLatitudeRef']

    if lon_ref == "W":
        longitude = -longitude
    if lat_ref == "S":
        latitude = -latitude

    # print('Coord = {} , {}'.format(latitude,longitude)) 

    # altitude pitch roll yaw of gps/autopilte
    gpsaltitude = convert_string_to_float(exif['Exif.GPSInfo.GPSAltitude'])
    gpspitch = np.mod(convert_string_to_float(xmp['Xmp.exif.GPSPitch']),360)
    gpsroll = np.mod(convert_string_to_float(xmp['Xmp.exif.GPSRoll']),360)
    gpsyaw = np.mod(convert_string_to_float(xmp['Xmp.exif.GPSTrack']),360)

    # altitude pitch roll yaw of camera
    altitude = gpsaltitude
    pitch = gpspitch
    roll = gpsroll
    yaw = gpsyaw

    eo = np.array([longitude, latitude, altitude, roll, pitch, yaw])

    return focal_length, orientation, eo, maker

def convert_dms_to_deg(dms):
    dms_split = dms.split(" ")
    d = convert_string_to_float(dms_split[0])
    m = convert_string_to_float(dms_split[1]) / 60
    s = convert_string_to_float(dms_split[2]) / 3600
    deg = d + m + s
    return deg

def convert_string_to_float(string):
    str_split = string.split('/')
    return int(str_split[0]) / int(str_split[1])    # unit: mm
