import turtle
import random
import math

n = int(input("How many cells horizontally: "))
m = int(input("How many cells vertically: "))

a = float(input("How many millimetres is a cell: "))
start_pos = [0,0]           #bottom left is 0,0 with first number as cells horizontal left to right, and second is cells vertical from top to bottom, it goes to [n,m]
curr_pos = start_pos        #the current cell position of the car
curr_pos_temp = curr_pos    #the temporary value that can be changed and used during the search algorithm
cell_pos = [a/2, a/2]       #the (current) position of the car in the cell itself
cell_pos_temp = cell_pos    #the temporary value that can be changed and used during the search algorithm


#walls is a n*m*2 array of boolean/ 1 or 2, which is a n*m grid of an array of 2, so n*m is the position, and the first bool of that position is if the bottom wall exist, and the second is if the left wall exist
walls = []                  #creates the n*m grid of cell walls
for i in range (n+1):         #THIS WILL PROBABLY BE REPLACED BY A SEPERATE PROGRAM THAT CREATES THE 2D ARRAY *WITH* THE WALLS (currently it's just empty)
    temp=[]
    for j in range (m+1):
        #temp.append([0,0])
        bottom = random.randint(0,1)
        left = random.randint(0,1)

        if (i == 0 or i == n): left = 1
        if (j == 0 or j == m): bottom = 1
        if i == n: bottom = 0
        if j == m: left = 0

        temp.append([bottom,left])
    walls.append(temp)


scan_output = []               #creates the 36*3 array for scanned values (same as the lidar values, being angle->average->min), not sure a good way to make an average dapa point
for i in range (36):
    scan_output.append([i*10,0,0])

def scan_sweep():

    len_sum = 0
    len_min = 0

    for angle in range(0,360,10):
        for offset in range(10):
            len_curr = scan_search(angle + offset)
            len_sum += len_curr
            len_min = min(len_min, len_curr)


def scan_search(angle, length):
    if (length>=2560):
        return 2560
    
    cell_pos_temp[0] += math.sin(angle)
    cell_pos_temp[1] += math.cos(angle)

    horz_collide = False
    vert_collide = False

    if cell_pos_temp[0] > a and walls[0,0,0]:
        curr_pos_temp[0] += 1
        cell_pos_temp[0] -= a

    elif cell_pos_temp[0] < 0:
        curr_pos_temp[0] -= 1
        cell_pos_temp[0] += a

        
    if cell_pos_temp[1] > a:
        curr_pos_temp[1] += 1
        cell_pos_temp[1] -= a

    elif cell_pos_temp[1] < 0:
        curr_pos_temp[1] -= 1
        cell_pos_temp[1] += a




    if (cell_pos_temp[0] > 0):
        length = scan_search(angle, length + 1)

    return(length)

#scan_sweep()

print(walls)
print(scan_output)

turtle.speed(0) #we can probably slow down the turtle move speed to slow down the program running speed

turtle.penup()
turtle.left(90)
turtle.goto(a * -(n+1) / 2 , a * -(m+1) / 2)

for i in range(n+1):
    for j in range(m+1):

        if (walls[i][j][0]):
            turtle.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j))
            turtle.pendown()
            turtle.goto(a * (-(n+1) / 2 + i + 1) , a * (-(m+1) / 2 + j))
            turtle.penup()

        if (walls[i][j][1]):
            turtle.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j))
            turtle.pendown()
            turtle.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j + 1))
            turtle.penup()
        


input()