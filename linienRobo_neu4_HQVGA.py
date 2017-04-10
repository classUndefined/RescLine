import sensor, image, time, pyb, ustruct, utime
from    pyb  import Pin, ExtInt

#++++++++++++++++++++++++++++++++++++ROIS+++++++++++++++++++++++++++++++++++++++++++++++++++

ROIS = [ # [ROI, weight]
        (0, 125, 160, 20, 1/1),
        (0, 100, 160, 20, 1/2), # rois || closer roi is worth more
        (0, 75, 160, 20, 1/3),
        (0, 50, 160, 20, 1/4),
        (0, 25, 160, 20, 1/5),
        (0, 0, 160, 20, 1/6)
       ]


#+++++++++++++++++++++++++++++++++Colour and Grayscale++++++++++++++++++++++++++++++++++++++
green               = [(0, 100, -60, -10, 0, 40)    ]        # generic_green_thresholds
GRAYSCALE_THRESHOLD = [(0, 20, -128, 127, -128, 127)]

#+++++++++++++++++++++++++++++++++Dec. and Def Send- and RecDate++++++++++++++++++++++++++++
spiSendData = bytes([1,0x03,0x05,0x07])  #Number of bytes is important here
spiRecData  = bytearray(4)                #The same number as above

#+++++++++++++++++++++++++++++++++Weigth++++++++++++++++++++++++++++++++++++++++++++++++++++
weight_sum = 0
for r in ROIS: weight_sum += r[4] # r[4] is the roi weight.

#+++++++++++++++++++++++++++++++++Sensor++++++++++++++++++++++++++++++++++++++++++++++++++++
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HQVGA) #220x160
sensor.skip_frames()
sensor.set_auto_gain(False)        # must be turned off for color tracking
sensor.set_auto_whitebal(False)    # must be turned off for color tracking
sensor.set_brightness(-1)

spi = pyb.SPI(2, pyb.SPI.SLAVE, polarity=0, phase=0)
pin = pyb.Pin("P3", pyb.Pin.IN, pull = pyb.Pin.PULL_UP)

spiSendData
spiRecData

green_active = False

img = sensor.snapshot() # Take a picture and return the image.


#++++++++++++++++++++++++++++++++++++functions++++++++++++++++++++++++++++++++++++++++++++++
def find_center_pos():

    global number_of_blobs

    centroid_sum = 0
    center_pos   = 0
    number_of_blobs = 0

    for r in ROIS:
     blobs = img.find_blobs(GRAYSCALE_THRESHOLD, roi=r[0:4], merge=False) # r[0:4] is roi tuple.
     if blobs:
         closest_blob = 0
         for i in range(len(blobs)):
             if i > 0:
                if blobs[i].y() > blobs[i-1].y():
                   closest_blob = i

         img.draw_rectangle(blobs[closest_blob].rect())
         img.draw_cross(blobs[closest_blob].cx(),blobs[closest_blob].cy())

         centroid_sum    += blobs[closest_blob].cx() * r[4] # r[4] is the roi weight.
         center_pos       = (centroid_sum / weight_sum) # Determine center of line.
         number_of_blobs += 1

         if number_of_blobs <= 2:
             center_pos = blobs[closest_blob].cx()

    return center_pos

def check_if_green():

    green_act  = False

    for r in ROIS:
     green_blobs = img.find_blobs(green, x_stride=1, pixels_threshold=160, margin=10,area_threshold=200, merge=True)
     if green_blobs:
        green_act = True

     return green_act

def find_green_dot():

    global number_of_green

    number_of_green   = 0
    green_dot_x       = 0

    for r in ROIS:
     green_blobs = img.find_blobs(green, x_stride=1, pixels_threshold=160, margin=3,area_threshold=200, merge=True)
     if green_blobs:
        for green_rect in green_blobs:
          img.draw_rectangle(green_rect.rect())
          img.draw_cross(green_rect.cx(), green_rect.cy())

          list_green_rects_x.append(green_rect.cx())
          list_green_rects_y.append(green_rect.cy())

        green_dot_x      = list_green_rects_x[0]
        number_of_green  = len(list_green_rects_x)
        return_tuple     = (green_dot_x, number_of_green)
        return return_tuple


#++++++++++++++++++++++++++++++++++++while-loop+++++++++++++++++++++++++++++++++++++++++++
while(True):
    spi.send(send=spiSendData, timeout=10)

    global green_dot_x

    img                = sensor.snapshot() # Take a picture and return the image.
    center_pos         = find_center_pos() #find center position
    center_horizontal  = 0

    list_green_rects_x = []
    list_green_rects_y = []

    case               = 0  # 1 = right | 2 = left | 3 = turn around |


    #++++++send data if no green+++++++++
    if center_pos == None:
        pass
    else:
        if center_pos < 220/2 + 30 and center_pos > 220/2 - 30:
            center_pos = 220/2
        spiSendData = bytes([int(center_pos),0,0, 0])
        img.draw_line([int(center_pos), 0, int(center_pos), 120])

    #+++++++++++Determine if green+++++++++++++++++++++
    green_active = check_if_green()

    #+++++++++++If there is green+++++++++++++++++++++
    if green_active:
        green_dot_x, number_of_green = find_green_dot()
        if number_of_green == 1:
            if green_dot_x > center_pos:
                case = 1
            if green_dot_x < center_pos:
                case = 2
        if number_of_green == 2:
            if list_green_rects_y[0] <= list_green_rects_y[1] + 10 and list_green_rects_y[0] >= list_green_rects_y[1] - 10:
                case = 3
            if list_green_rects_y[0] > list_green_rects_y[1] + 20 or list_green_rects_y[0] < list_green_rects_y[1] - 20:
                if list_green_rects_x[0] <  list_green_rects_x[1] - 30:
                    case = 2
                if list_green_rects_x[0] >  list_green_rects_x[1] + 30:
                    case = 1

        spiSendData = bytes([int(center_pos),int(green_dot_x),number_of_green, case])

        print("Green pos:  " + str(green_dot_x))
        print("Green numb: " + str(number_of_green))
        print("Green x: " + str(list_green_rects_x))
        print("Green y: " + str(list_green_rects_y))


    #+++prints++++
    print("Center pos: " + str(center_pos))
    print("Blobs numb: " + str(number_of_blobs))
    print("---------------------------------")
