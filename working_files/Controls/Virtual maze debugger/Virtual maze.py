import turtle
import random
import math

turt_maze = turtle.Turtle()
turt_scan = turtle.Turtle()


n = int(input("How many cells horizontally: "))
m = int(input("How many cells vertically: "))

a = float(input("How many millimetres is a cell: "))
start_pos = [0,0]           #bottom left is 0,0 with first number as cells horizontal left to right, and second is cells vertical from top to bottom, it goes to [n,m]
curr_pos = start_pos        #the current cell position of the car
curr_pos_temp = curr_pos    #the temporary value that can be changed and used during the search algorithm
cell_pos = [a/2, a/2]       #the (current) position of the car in the cell itself
cell_pos_temp = cell_pos    #the temporary value that can be changed and used during the search algorithm


#walls is a n*m*2 array of boolean/ 0 or 1, which is a n*m grid of an array of 2, so n*m is the position, and the first bool of that position is if the bottom wall exist, and the second is if the left wall exist
walls = []
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

    for angle in range(0,36):   #sweeps through the 36 main sections
    
        len_sum = 0             #reset this section's total length (for average) and minimum length
        len_min = 3000
        for offset in range(-5, 5, 1):    #sweeps through the 10 degrees of this segment, could be made finer or coarser
            global curr_pos
            global curr_pos_temp 
            curr_pos_temp = curr_pos

            global cell_pos
            global cell_pos_temp 
            cell_pos_temp = cell_pos

            len_curr = scan_search((angle * 10 + offset + 360) % 360, 0)
            print(len_curr)
            len_sum += len_curr     #adds total length and find's minimum length
            len_min = min(len_min, len_curr)
        
        scan_output[angle] = [angle*10, len_sum/10, len_min]    #saves current angle, average length and minimum length to the scan array


def scan_search(angle, length):

    global curr_pos_temp
    global cell_pos_temp

    if (length>=2560):          #exit case, emulating if the scan goes beyond the lidar's maximum scan distance
        return 2560.0
    
    angle = angle * math.pi / 180

    cell_pos_temp[0] += math.sin(angle)     #adds to the distance by 1 in the angle theta
    cell_pos_temp[1] += math.cos(angle)
    print(cell_pos_temp)

    collision = False                    #booleans for if collision happened


    if cell_pos_temp[0] > a:    #checks if it moves beyond right side of cell
        if walls[curr_pos_temp[0] + 1][curr_pos_temp[1]][1] == 1:  #if the right side of the cell exists a wall
            collision = True
        else:
            curr_pos_temp[0] += 1
            cell_pos_temp[0] -= a

    elif cell_pos_temp[0] < 0:  #checks if it moves beyond left side of cell
        if walls[curr_pos_temp[0]][curr_pos_temp[1]][1] == 1:  #if the left side of the cell exists a wall
            collision = True
        else:
            curr_pos_temp[0] -= 1
            cell_pos_temp[0] += a

        
    if cell_pos_temp[1] > a:    #checks if it moves beyond up side of cell
        if walls[curr_pos_temp[0]][curr_pos_temp[1] + 1][0] == 1:  #if the up side of the cell exists a wall
            collision = True
        else:
            curr_pos_temp[1] += 1
            cell_pos_temp[1] -= a

    elif cell_pos_temp[1] < 0:  #checks if it moves beyond down side of cell
        if walls[curr_pos_temp[0]][curr_pos_temp[1]][0] == 1:  #if the down side of the cell exists a wall
            collision = True
        else:
            curr_pos_temp[1] -= 1
            cell_pos_temp[1] += a



    if not collision:   #if a collision does not occur, continue recursion and continue scanning
        length = scan_search(angle, length + 1)

    return(length)      #returns length (at collision or maximum distance)

def scan_draw():
    for section in scan_output:
        print()
        print(section)
        print(section[0])
        turt_scan.goto(a * (n+1) / 2 , 0)
        turt_scan.setheading(section[0])
        turt_scan.pendown()
        turt_scan.forward(section[1])
        turt_scan.penup()
        turt_scan.forward(section[2]-section[1])
        turt_scan.dot()

#scan_sweep()

print(walls)
print(scan_output)

        
#turt_scan.speed(0)
turt_scan.penup()
turt_maze.speed(0) #we can probably slow down the turtle move speed to slow down the program running speed

turt_maze.penup()
turt_maze.left(90)
turt_maze.goto(a * -(n+1) / 2 , a * -(m+1) / 2)

for i in range(n+1):
    for j in range(m+1):

        if (walls[i][j][0]):
            turt_maze.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j))
            turt_maze.pendown()
            turt_maze.goto(a * (-(n+1) / 2 + i + 1) , a * (-(m+1) / 2 + j))
            turt_maze.penup()

        if (walls[i][j][1]):
            turt_maze.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j))
            turt_maze.pendown()
            turt_maze.goto(a * (-(n+1) / 2 + i) , a * (-(m+1) / 2 + j + 1))
            turt_maze.penup()


turt_maze.goto(a * (-(n+1) / 2 + curr_pos[0]) + cell_pos[0], a * (-(m+1) / 2 + curr_pos[1]) + cell_pos[0])


input()


scan_sweep()
scan_draw()


input()