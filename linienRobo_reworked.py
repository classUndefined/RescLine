import sensor, image, time, pyb, ustruct, utime
from    pyb  import Pin, ExtInt

#++++++++++++++++++++++++++++++++++++ROIS+++++++++++++++++++++++++++++++++++++++++++++++++++

ROIS = [ # [ROI, weight]
        (0, 100, 160, 20, 1/1), # rois || closer roi is worth more
        (0, 75, 160, 20, 1/2),
        (0, 50, 160, 20, 1/3),
        (0, 25, 160, 20, 1/4),
        (0, 0, 160, 20, 1/5)
       ]

#+++++++++++++++++++++++++++++++++Colour and Grayscale++++++++++++++++++++++++++++++++++++++
green               = [(15, 100, -50, -10, 0, 40)    ]        # generic_green_thresholds
GRAYSCALE_THRESHOLD = [(0, 30, -128, 127, -128, 127)]

#+++++++++++++++++++++++++++++++++Dec. and Def Send- and RecDate++++++++++++++++++++++++++++
spiSendData = bytes([1,0x03,0x05,0x07])  #Number of bytes is important here
spiRecData  = bytearray(4)                #The same number as above

#+++++++++++++++++++++++++++++++++Weigth++++++++++++++++++++++++++++++++++++++++++++++++++++
weight_sum = 0
for r in ROIS: weight_sum += r[4] # r[4] is the roi weight.

#+++++++++++++++++++++++++++++++++Sensor++++++++++++++++++++++++++++++++++++++++++++++++++++
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA) #160x120
sensor.skip_frames()
sensor.set_auto_gain(False)        # must be turned off for color tracking
sensor.set_auto_whitebal(False)    # must be turned off for color tracking
sensor.set_brightness(+1)

spi = pyb.SPI(2, pyb.SPI.SLAVE, polarity=0, phase=0)

spi = pyb.SPI(2, pyb.SPI.SLAVE, polarity=0, phase=0)
pin = pyb.Pin("P3", pyb.Pin.IN, pull = pyb.Pin.PULL_UP)

spiSendData
spiRecData

img = sensor.snapshot() # Take a picture and return the image.

#++++++++++++++++++++++++++++++++++++functions++++++++++++++++++++++++++++++++++++++++++++++
def find_center_pos():

    global number_of_blobs
    global cross_road_begin
    global on_cross_road

    cross_road_begin  = False
    on_cross_road     = False
    centroid_sum      = 0
    center_pos        = 0
    number_of_blobs   = 0

    list_blob_size    = []
    list_empty        = []

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
         list_blob_size.append(blobs[closest_blob].w())

         if len(list_blob_size) == 5:
             print("Sizes: " + str(list_blob_size))

             if list_blob_size[4] >= 158:
                cross_road_begin  = True
             if list_blob_size[2] >= 158 and list_blob_size[3] >= 158:
                 on_cross_road  = True


             list_blob_size = list_empty;

         centroid_sum    += blobs[closest_blob].cx() * r[4] # r[4] is the roi weight.
         center_pos       = (centroid_sum / weight_sum) # Determine center of line.
         number_of_blobs += 1

         if number_of_blobs <= 2:
             center_pos = blobs[closest_blob].cx()

    return center_pos


def check_if_green():

    green_act  = False

    for r in ROIS:
     green_blobs = img.find_blobs(green, pixels_threshold=160, margin=10,area_threshold=200, merge=True)
     if green_blobs:
        green_act = True

     return green_act

def find_green_dot():

    global number_of_green

    number_of_green   = 0
    green_dot_x       = 0

    for r in ROIS:
     green_blobs = img.find_blobs(green, pixels_threshold=160, margin=5,area_threshold=200, merge=True)
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

    timer = time.clock()

    global green_dot_x

    img                = sensor.snapshot() # Take a picture and return the image.
    center_pos         = find_center_pos() #find center position
    center_horizontal  = 0

    list_green_rects_x = []
    list_green_rects_y = []

    case               = 0  # 1 = right | 2 = left | 3 = turn around |
    send_on_cross      = 0  # 0 = not on cross | 1 = on cross
    number_of_green    = 0


    #+++++++++++Determine if green+++++++++++++++++++++
    green_active = check_if_green()

    #+++++++++++If there is green+++++++++++++++++++++
    if cross_road_begin == False:
        if green_active:
            green_dot_x, number_of_green = find_green_dot()
            if number_of_green == 1:
                if green_dot_x > center_pos:
                    case = 1
                if green_dot_x < center_pos:
                    case = 2

            if number_of_green == 2:
                if list_green_rects_y[0] <= list_green_rects_y[1] + 10 and list_green_rects_y[0] >= list_green_rects_y[1] - 10:
                    if on_cross_road == True:
                        send_on_cross = 1
                    case = 3
                if list_green_rects_y[0] > list_green_rects_y[1] + 20 or list_green_rects_y[0] < list_green_rects_y[1] - 20:
                    if list_green_rects_x[0] <  list_green_rects_x[1] - 30:
                        if on_cross_road == True:
                            send_on_cross = 1
                        case = 2
                    if list_green_rects_x[0] >  list_green_rects_x[1] + 30:
                        case = 1


            if number_of_green == 3:
                number_left  = 0
                number_right = 0
                for i in range(len(list_green_rects_x)):
                    if  list_green_rects_x[i] < center_pos:
                        number_left += 1
                    if  list_green_rects_x[i] > center_pos:
                        number_right += 1
                if number_left > number_right:
                    if on_cross_road == True:
                        send_on_cross = 1
                    case = 2
                else:
                    if on_cross_road == True:
                        send_on_cross = 1
                    case = 1

           # if cross_road_begin == False:
            #    spiSendData = bytes([80,int(green_dot_x),send_on_cross, case])

            print("Green pos:  " + str(green_dot_x))

            print("Green x:    " + str(list_green_rects_x))
            print("Green y:    " + str(list_green_rects_y))


    #if cross_road_begin == True:
    #    spiSendData      = bytes([80,0,0,0])

    if number_of_green == 0:
        #++++++send data if no green+++++++++
        if center_pos == None:
            pass
        else:
            spiSendData = bytes([int(center_pos),0,0,0])
            img.draw_line([int(center_pos), 0, int(center_pos), 120])
    else:
         spiSendData = bytes([int(center_pos),int(green_dot_x),send_on_cross, case])

    #+++prints++++
    print("Case:       " + str(case))
    print("Cross Road: " + str(cross_road_begin))
    print("Center pos: " + str(center_pos))
    print("Blobs numb: " + str(number_of_blobs))
    print("Green numb: " + str(number_of_green))
    print("---------------------------------")

