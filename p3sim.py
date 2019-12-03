from __future__ import print_function
import copy
import os
import generators
# Function List:
# 0. getFaults: gets the faults from the file
# 1. genFaultList: generates all of the faults and prints them to a file
# 2. netRead: read the benchmark file and build circuit netlist
# 3. gateCalc: function that will work on the logic of each gate
# 4. inputRead: function that will update the circuit dictionary made in netRead to hold the line values
# 5. basic_sim: the actual simulation
# 6. main: The main function

#gets all of the faults from the file


def getFaults(faultFile):
    #opens the file
    inFile = open(faultFile, "r")

    faults = []

    #goes line by line and adds the faults to arrays
    for line in inFile:
        # Do nothing else if empty lines, ...
        if (line == "\n"):
            continue
        # ... or any comments
        if (line[0] == "#"):
            continue
        
        line = line.replace("\n", "")
        data = [False]
        data.append(line.split("-"))

        faults.append(data)
    inFile.close()
    return faults

#generates all of the faults
def genFaultList(circuit, faultFile, circuitName):
    numFaults = 0
    outFile = open(faultFile, "w")
    
    outFile.write("# " + circuitName + "\n")
    outFile.write("# full SSA fault list\n\n")


    #handles the inputs
    for input in circuit["INPUTS"][1]:
        outFile.write(input[5:] + "-SA-0\n")
        outFile.write(input[5:] + "-SA-1\n")
        numFaults += 2

    for wire in circuit["GATES"][1]:
        outFile.write(wire[5:] + "-SA-0\n")
        outFile.write(wire[5:] + "-SA-1\n")
        numFaults += 2

        for inWire in circuit[wire][1]:
            outFile.write(wire[5:] + "-IN-" + inWire[5:] + "-SA-0\n")
            outFile.write(wire[5:] + "-IN-" + inWire[5:] + "-SA-1\n")
            numFaults += 2

    outFile.write("\n# total faults: " + str(numFaults))
    outFile.close()

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Neatly prints the Circuit Dictionary:
def printCkt (circuit):
    print("INPUTS:")
    for x in circuit["INPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nOUTPUTS:")
    for x in circuit["OUTPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nGATES:")
    for x in circuit["GATES"][1]:
        print(x + "= ", end='')
        print(circuit[x])
    print()


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Reading in the Circuit gate-level netlist file:
def netRead(netName):
    # Opening the netlist file:
    netFile = open(netName, "r")
    inputCounter=0

    # temporary variables
    inputs = []     # array of the input wires
    outputs = []    # array of the output wires
    gates = []      # array of the gate list
    inputBits = 0   # the number of inputs needed in this given circuit


    # main variable to hold the circuit netlist, this is a dictionary in Python, where:
    # key = wire name; value = a list of attributes of the wire
    circuit = {}

    # Reading in the netlist file line by line
    for line in netFile:

        # NOT Reading any empty lines
        if (line == "\n"):
            continue

        # Removing spaces and newlines
        line = line.replace(" ","")
        line = line.replace("\n","")

        # NOT Reading any comments
        if (line[0] == "#"):
            continue

        # @ Here it should just be in one of these formats:
        # INPUT(x)
        # OUTPUT(y)
        # z=LOGIC(a,b,c,...)

        # Read a INPUT wire and add to circuit:
        if (line[0:5] == "INPUT"):
            inputCounter=inputCounter+1
            # Removing everything but the line variable name
            line = line.replace("INPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Format the variable name to wire_*VAR_NAME*
            line = "wire_" + line

            # Error detection: line being made already exists
            if line in circuit:
                msg = "NETLIST ERROR: INPUT LINE \"" + line + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
                print(msg + "\n")
                return msg

            # Appending to the inputs array and update the inputBits
            inputs.append(line)

            # add this wire as an entry to the circuit dictionary
            circuit[line] = ["INPUT", line, False, 'U']

            inputBits += 1
#            print(line)
#            print(circuit[line])
            continue

        # Read an OUTPUT wire and add to the output array list
        # Note that the same wire should also appear somewhere else as a GATE output
        if line[0:6] == "OUTPUT":
            # Removing everything but the numbers
            line = line.replace("OUTPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Appending to the output array
            outputs.append("wire_" + line)
            continue

        # Read a gate output wire, and add to the circuit dictionary
        lineSpliced = line.split("=") # splicing the line at the equals sign to get the gate output wire
        gateOut = "wire_" + lineSpliced[0]

        # Error detection: line being made already exists
        if gateOut in circuit:
            msg = "NETLIST ERROR: GATE OUTPUT LINE \"" + gateOut + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
            print(msg+"\n")
            return msg

        # Appending the dest name to the gate list
        gates.append(gateOut)

        lineSpliced = lineSpliced[1].split("(") # splicing the line again at the "("  to get the gate logic
        logic = lineSpliced[0].upper()


        lineSpliced[1] = lineSpliced[1].replace(")", "")
        terms = lineSpliced[1].split(",")  # Splicing the the line again at each comma to the get the gate terminals
        # Turning each term into an integer before putting it into the circuit dictionary
        terms = ["wire_" + x for x in terms]

        # add the gate output wire to the circuit dictionary with the dest as the key
        circuit[gateOut] = [logic, terms, False, 'U']
#        print(gateOut)
#        print(circuit[gateOut])

    # now after each wire is built into the circuit dictionary,
    # add a few more non-wire items: input width, input array, output array, gate list
    # for convenience
    
    circuit["INPUT_WIDTH"] = ["input width:", inputBits]
    circuit["INPUTS"] = ["Input list", inputs]
    circuit["OUTPUTS"] = ["Output list", outputs]
    circuit["GATES"] = ["Gate list", gates]

#    print("\n bookkeeping items in circuit: \n")
#    print(circuit["INPUT_WIDTH"])
#    print(circuit["INPUTS"])
#    print(circuit["OUTPUTS"])
#    print(circuit["GATES"])


    #return circuit
    return [circuit, inputCounter]


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: calculates the output value for each logic gate
def gateCalc(circuit, node, memory):
    
    # terminal will contain all the input wires of this logic gate (node)
    terminals = list(circuit[node][1])  


    # If the node is an Buffer gate output, solve and return the output
    if circuit[node][0] == "BUFF":
        if circuit[terminals[0]][3] == '0':
            circuit[node][3] = '0'
        elif circuit[terminals[0]][3] == '1':
            circuit[node][3] = '1'
        elif circuit[terminals[0]][3] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1
        return [circuit, memory];



    # If the node is an Inverter gate output, solve and return the output
    if circuit[node][0] == "NOT":
        if circuit[terminals[0]][3] == '0':
            circuit[node][3] = '1'
        elif circuit[terminals[0]][3] == '1':
            circuit[node][3] = '0'
        elif circuit[terminals[0]][3] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1
        return [circuit, memory];


    elif circuit[node][0] == "DFF":
        circuit[node][3]=memory[node]
        #print("memory node: " + str(memory[node]))
        unknownTerm = False  # This will become True if at least one unknown terminal is found
        print("dff terminals: " + str(terminals))
        print("circuit terminals: " + str(circuit[terminals[0]][3]))

        for term in terminals:  
            if circuit[term][3] == '0':
                circuit[node][3] = '0'
            elif circuit[term][3] =='1':
                circuit[node][3]='1'
                break
            if circuit[term][3] == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = '1'
            elif circuit[node][3] == '0': 
                circuit[node][3] = '0'
        print("final node: " + str(circuit[node][3]))

        return [circuit, memory];

        # for term in terminals:  
        #     if circuit[term][3] == '0':
        #         circuit[node][3] = '0'
        #         memory[node]='0'

        #     elif circuit[term][3] == '1':
        #         circuit[node][3]='1'
        #         memory[node]='1'


        # if circuit[terminals[0]][3] == '0':
        #     circuit[node][3] = '0'
        #     memory[node]='0'
        # elif circuit[terminals[0]][3] == '1':
        #     circuit[node][3] = '1'
        #     memory[node]='1'
        # elif circuit[terminals[0]][3] == "U":
        #     circuit[node][3] = "U"
        #     memory[node]="U"
        # else:  # Should not be able to come here
        #     return -1
        return [circuit, memory];


      #TV input
      #C
      #B
      #A
     #MUX(A,B,C) -> MUX(A B SEL)

     #If SEL=0, OUT=A
     #IF SEL=1, OUT=B
    elif circuit[node][0] == "MUX":

        if circuit[terminals[2]][3] == '0': #sel bit
            circuit[node][3] = circuit[terminals[0]][3]
        elif circuit[terminals[2]][3] == '1':
            circuit[node][3] = circuit[terminals[1]][3]
        elif circuit[terminals[2]][3] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1

        return [circuit, memory];  


    # If the node is an AND gate output, solve and return the output
    elif circuit[node][0] == "AND":

        # Initialize the output to 1
        circuit[node][3] = '1'

        # Initialize also a flag that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 at any input terminal, AND output is 0. If there is an unknown terminal, mark the flag
        # Otherwise, keep it at 1
        for term in terminals:  
            if circuit[term][3] == '0':
                circuit[node][3] = '0'
                break
            if circuit[term][3] == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return [circuit, memory];

    # If the node is a NAND gate output, solve and return the output
    elif circuit[node][0] == "NAND":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 terminal, NAND changes the output to 1. If there is an unknown terminal, it
        # changes to "U" Otherwise, keep it at 0
        for term in terminals:
            if circuit[term][3] == '0':
                circuit[node][3] = '1'
                break
            if circuit[term][3] == "U":
                unknownTerm = True
                break

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return [circuit, memory];

    # If the node is an OR gate output, solve and return the output
    elif circuit[node][0] == "OR":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, OR changes the output to 1. Otherwise, keep it at 0
        for term in terminals:
            if circuit[term][3] == '1':
                circuit[node][3] = '1'
                break
            if circuit[term][3] == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return [circuit, memory];




    # If the node is an NOR gate output, solve and return the output
    if circuit[node][0] == "NOR":
        # Initialize the output to 1
        circuit[node][3] = '1'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, NOR changes the output to 0. Otherwise, keep it at 1
        for term in terminals:
            if circuit[term][3] == '1':
                circuit[node][3] = '0'
                break
            if circuit[term][3] == "U":
                unknownTerm = True
        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return [circuit, memory];

    # If the node is an XOR gate output, solve and return the output
    if circuit[node][0] == "XOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there are an odd number of terminals, XOR outputs 1. Otherwise, it should output 0
        for term in terminals:
            if circuit[term][3] == '1':
                count += 1  # For each 1 bit, add one count
            if circuit[term][3] == "U":
                circuit[node][3] = "U"
                return [circuit, memory];

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '1'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '0'
        return [circuit, memory];

    # If the node is an XNOR gate output, solve and return the output
    elif circuit[node][0] == "XNOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there is a single 1 terminal, XNOR outputs 0. Otherwise, it outputs 1
        for term in terminals:
            if circuit[term][3] == '1':
                count += 1  # For each 1 bit, add one count
            if circuit[term][3] == "U":
                circuit[node][3] = "U"
                return [circuit, memory];

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '1'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '0'
        return [circuit, memory];

    # Error detection... should not be able to get at this point
    return [circuit[node][0], memory];


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Updating the circuit dictionary with the input line, and also resetting the gates and output lines
def inputRead(circuit, line):
    # Checking if input bits are enough for the circuit
    if len(line) < circuit["INPUT_WIDTH"][1]:
        return -1

    # Getting the proper number of bits:
    line = line[(len(line) - circuit["INPUT_WIDTH"][1]):(len(line))]

    # Adding the inputs to the dictionary
    # Since the for loop will start at the most significant bit, we start at input width N
    i = circuit["INPUT_WIDTH"][1] - 1
    inputs = list(circuit["INPUTS"][1])
    # dictionary item: [(bool) If accessed, (int) the value of each line, (int) layer number, (str) origin of U value]
    for bitVal in line:
        bitVal = bitVal.upper() # in the case user input lower-case u
        circuit[inputs[i]][3] = bitVal # put the bit value as the line value
        circuit[inputs[i]][2] = True  # and make it so that this line is accessed

        # In case the input has an invalid character (i.e. not "0", "1" or "U"), return an error flag
        if bitVal != "0" and bitVal != "1" and bitVal != "U":
            return -2
        i -= 1 # continuing the increments

    return circuit

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: the actual simulation #
def basic_sim(circuit, memory):
    # QUEUE and DEQUEUE
    # Creating a queue, using a list, containing all of the gates in the circuit
    queue = list(circuit["GATES"][1])
    #memory={}
    # neighbors=list(circuit[queue[0]][1])
    # print("neighbors: " +  str(circuit[queue[0]][1]))

    i = 1
    ct=0
    i2=0
    while (i2 <5):
        i2=i2+1
        while True:
            i -= 1
            # If there's no more things in queue, done
            if len(queue) == 0:
                break

            # Remove the first element of the queue and assign it to a variable for us to use
            curr = queue[0]
            queue.remove(curr)
            neighbors=list(circuit[curr][1]) #inputs needed to calculate gate output

            # initialize a flag, used to check if every terminal has been accessed
            term_has_value = True

            if(str(circuit[curr][0]) == "DFF"):
                    if curr not in memory:
                        print("memory: " + str(memory)+ " \ncurr: " + str(curr))
                        memory[curr]='U'

            # Check if the terminals have been accessed
            for term in circuit[curr][1]:
                

                #check if the inputs needed to calculate gate output have been calculated themselves
                if(str(circuit[curr][0]) == "DFF"):
                    dL=list(set(neighbors)-set(queue))
                    print("dLbasic_sim: "+ str(dL))
                    if dL: #if the inputs needed to calculate the gate havent been calulated yet, skip
                        continue

                if not circuit[term][2]:
                    if(str(circuit[curr][0]) == "DFF"):
                        dL=list(set(neighbors)-set(queue))
                        print("dLbasic_sim: "+ str(dL))
                        if dL: #if the inputs needed to calculate the gate havent been calulated yet, skip
                            term_has_value = False
                            continue

                    else:
                        term_has_value = False
                        break

            if term_has_value:
                
                #checks to make sure the gate output has not already been set
                if(circuit[curr][2] == False):
                    circuitIM = gateCalc(circuit, curr, memory)
                    circuit=circuitIM[0]
                    memory=circuitIM[1]


                circuit[curr][2] = True

                # ERROR Detection if LOGIC does not exist
                if isinstance(circuit, str):
                    print(circuit)
                    return circuit

    #            print("Progress: updating " + curr + " = " + circuit[curr][3] + " as the output of " + circuit[curr][0] + " for:")
    #            for term in circuit[curr][1]:
    #                print(term + " = " + circuit[term][3])
    #            print("\n")

            else:
                # If the terminals have not been accessed yet, append the current node at the end of the queue
                queue.append(curr)

        

    print(memory)
    return [circuit, memory]


def userIn():
    while True:
        print("Choose what you'd like to do (1, 2, or 3): " + "\n 1: Test Vector Generation" + "\n 2: Fault Coverage Simulation \n")
        opt=input()

        if opt not in ("1", "2"):
            print("Input not recognized. \n")
            continue
        else:
            return opt
            #break  


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Main Function
def main():
    # **************************************************************************************************************** #
    # NOTE: UI code; Does not contain anything about the actual simulation

    # Used for file access
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in

    print("Circuit Simulator:")
##########################################################################################
    # Select circuit benchmark file, default is circuit.bench
    

    while True:
        cktFile = "circuit.bench"   
        print("\n Read circuit benchmark file: use " + cktFile + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":
            break
        else:
            cktFile = os.path.join(script_dir, userInput)
            if not os.path.isfile(cktFile):
                print("File does not exist. \n")
            else:
                break

    print("\n Reading " + cktFile + " ... \n")
    tempNetRead=netRead(cktFile)
    ##---------------Calling modified netRead here ---------#
    #circuit = netRead(cktFile)
    circuit=tempNetRead[0]
    myN=tempNetRead[1]
    ##---------------Calling modified netRead here ---------#

    print("\n Finished processing benchmark file and built netlist dictionary: \n")
    # Uncomment the following line, for the neater display of the function and then comment out print(circuit)
#    printCkt(circuit)
    #print(circuit)

    # keep an initial (unassigned any value) copy of the circuit for an easy reset
    newCircuit = circuit

    #select fault file, default is  full_f_list.txt
################################################"WRITE FULL FAULT LIST###########################"
    while True:
        faultListName = "full_f_list.txt"
        print("\n Write full fault list file: use " + faultListName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":
            break
        else:
            faultListName = os.path.join(script_dir, userInput)
            break
################################################"WRITE FULL FAULT LIST###########################"
    
    #generates the fault list
    genFaultList(circuit, faultListName, cktFile) 

    #Select input fault file, default is f_list.txt
    while True:
        faultInputName = "full_f_list.txt"
        print("\n Read input fault file: use " + faultInputName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":

            break
        else:
            faultInputName = os.path.join(script_dir, userInput)
            if not os.path.isfile(faultInputName):
                print("File does not exist. \n")
            else:
                break

    #gets the faults that need to be tested
    faults = getFaults(faultInputName)

    # Select input file, default is input.txt
    while True:
        inputName = "input.txt"
        print("\n Read input vector file: use " + inputName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":

            break
        else:
            inputName = os.path.join(script_dir, userInput)
            if not os.path.isfile(inputName):
                print("File does not exist. \n")
            else:
                break

    # Select output file, default is output.txt
    while True:
        outputName = "fault_sim_result.txt"
        print("\n Write result file: use " + outputName + "?" + " Enter to accept or type filename: ")
        userInput = input()
        if userInput == "":
            break
        else:
            outputName = os.path.join(script_dir, userInput)
            break

    # Note: UI code;
    # **************************************************************************************************************** #

    print("\n *** Simulating the" + inputName + " file and will output in" + outputName + "*** \n")
    inputFile = open(inputName, "r")
    outputFile = open(outputName, "w")

    outputFile.write("# fault sim result\n")
    outputFile.write("# input: " + cktFile + "\n")
    outputFile.write("# input: " + inputName + "\n")
    outputFile.write("# input: " + faultInputName + "\n\n\n")

   

    # Runs the simulator for each line of the input file
##############################################################LOOK FOR N HERE###################################    
    testVectorNum = 1
    for line in inputFile:
        print("line: " + line)
        # Initializing output variable each input line
        output = ""

        # Do nothing else if empty lines, ...
        if (line == "\n"):
            continue
        # ... or any comments
        if (line[0] == "#"):
            continue

        # Removing the the newlines at the end and then output it to the txt file
        line = line.replace("\n", "")
        outputFile.write("tv" + str(testVectorNum) + " = " + line)

        #updates testVectorNum for the next one
        testVectorNum += 1

        # Removing spaces
        line = line.replace(" ", "")
        
#        print("\n before processing circuit dictionary...")
        # Uncomment the following line, for the neater display of the function and then comment out print(circuit)
        #printCkt(circuit)
#        print(circuit)

#        print("\n ---> Now ready to simulate INPUT = " + line)
        circuit = inputRead(circuit, line)
        # Uncomment the following line, for the neater display of the function and then comment out print(circuit)
        #printCkt(circuit)
#        print(circuit)

        if circuit == -1:
            print("INPUT ERROR: INSUFFICIENT BITS")
            outputFile.write(" -> INPUT ERROR: INSUFFICIENT BITS" + "\n")
            # After each input line is finished, reset the netList
            circuit = newCircuit
            print("...move on to next input\n")
            continue
        elif circuit == -2:
            print("INPUT ERROR: INVALID INPUT VALUE/S")
            outputFile.write(" -> INPUT ERROR: INVALID INPUT VALUE/S" + "\n")
            # After each input line is finished, reset the netList
            circuit = newCircuit
            print("...move on to next input\n")
            continue
        memory={}
        circuitIN = basic_sim(circuit, memory)
        circuit=circuitIN[0]
        memory=circuitIN[1]
        # circuitIN = basic_sim(circuit, memory)
        # circuit=circuitIN[0]
        # memory=circuitIN[1]
        # circuitIN = basic_sim(circuit, memory)
        # circuit=circuitIN[0]
        # memory=circuitIN[1]
        # circuitIN = basic_sim(circuit, memory)
        # circuit=circuitIN[0]
        # memory=circuitIN[1]

        print("\n *** Finished simulation - resulting circuit: \n")
        # Uncomment the following line, for the neater display of the function and then comment out print(circuit)
        #printCkt(circuit)
 #       print(circuit)

        for y in circuit["OUTPUTS"][1]:
            if not circuit[y][2]:
                output = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                break
            output = str(circuit[y][3]) + output

        print("\n *** Summary of simulation: ")
        print(line + " -> " + output + " written into output file. \n")
        outputFile.write(" -> " + output + " (good)\n")
        outputFile.write("detected:\n")

        #after the output is written run the faults
        print("\n *** Now running fault tests *** \n")

        for faultLine in faults:

            #creates a copy of the circuit to be used for fault testing
            faultCircuit = copy.deepcopy(circuit)

            for key in faultCircuit:
                if (key[0:5]=="wire_"):
                    faultCircuit[key][2] = False
                    faultCircuit[key][3] = 'U'
            
            #sets up the inputs for the fault circuit
            faultCircuit = inputRead(faultCircuit, line)

            #handles stuck at faults
            if(faultLine[1][1] == "SA"):
                for key in faultCircuit:
                    try:
                       if(faultLine[1][0] == key[5:]):
                            #print(faultLine[1][0])
                            #print(key[5:])
                            print('A')
                            faultCircuit[key][2] = True
                            faultCircuit[key][3] = faultLine[1][2]
                            #print('B')
                    except:
                        pass

            #handles in in stuck at faults by making a new "wire"
            elif(faultLine[1][1] == "IN"):
                faultCircuit["faultWire"] = ["FAULT", "NONE", True, faultLine[1][4]]
                print('C')

                #finds the input that needs to be changed to the fault line
                for key in faultCircuit:
                    print('D')
                    if(faultLine[1][0] == key[5:]):
                        inputIndex = 0
                        print('F')
                        for gateInput in faultCircuit[key][1]:
                            print('G')
                            if(faultLine[1][2] == gateInput[5:]):
                                faultCircuit[key][1][inputIndex] = "faultWire"
                                print('H')
                            
                            inputIndex += 1
################################FAULT RUNNER###################################################################            
            #runs Circuit Simulation
            memory={}
            faultCircuitIM = basic_sim(faultCircuit, memory)
            faultCircuit=faultCircuitIM[0]
            memory=faultCircuitIM[1]
            # faultCircuit=faultCircuitIM[0]
            # memory=faultCircuitIM[1]
            # faultCircuit=faultCircuitIM[0]
            # memory=faultCircuitIM[1]

            #gets the output
            faultOutput = ""
            for y in faultCircuit["OUTPUTS"][1]:
                if not faultCircuit[y][2]:
                    faultOutput = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                    break
                faultOutput = str(faultCircuit[y][3]) + faultOutput

            #checks to see if the fault was detected
            if(output != faultOutput):
                faultLine[0] = True
                
                #prints out the fault if it is a SA
                if(faultLine[1][1] == "SA"):
                    outputFile.write(faultLine[1][0] + "-" + faultLine[1][1] + "-" + faultLine[1][2] + ": ")
                    outputFile.write(line + " -> " + faultOutput + "\n")
                
                #prints out the fault if it is IN-SA
                elif(faultLine[1][1] == "IN"):
                    outputFile.write(faultLine[1][0] + "-" + faultLine[1][1] + "-" + faultLine[1][2] + "-" + faultLine[1][3] + "-" + faultLine[1][4] + ": ")
                    outputFile.write(line + " -> " + faultOutput + "\n")


        #adds extra line of space to file for formatiing
        outputFile.write("\n")
        # After each input line is finished, reset the circuit
        print("\n *** Now resetting circuit back to unknowns... \n")
       
        for key in circuit:
            if (key[0:5]=="wire_"):
                circuit[key][2] = False
                circuit[key][3] = 'U'

        print("\n circuit after resetting: \n")
        # Uncomment the following line, for the neater display of the function and then comment out print(circuit)
        #printCkt(circuit)
#        print(circuit)

        print("\n*******************\n")
###########################----------------------------FAULT COVERAGE SECTION-------------------------------------##
    totalFaults = 0
    detectedFaults = 0
    for faultLine in faults:
        totalFaults += 1
        if(faultLine[0] == True):
            detectedFaults += 1
    
    undetectedFaults = totalFaults - detectedFaults
    
    outputFile.write("total detected faults: " + str(detectedFaults))
    outputFile.write("\n\nundetected faults: " + str(undetectedFaults) + "\n")

    for faultLine in faults:
        if(faultLine[0] == False):
            #prints out the fault if it is a SA
            if(faultLine[1][1] == "SA"):
                outputFile.write(faultLine[1][0] + "-" + faultLine[1][1] + "-" + faultLine[1][2] + "\n")

            #prints out the fault if it is IN-SA
            elif(faultLine[1][1] == "IN"):
                outputFile.write(faultLine[1][0] + "-" + faultLine[1][1] + "-" + faultLine[1][2] + "-" + faultLine[1][3] + "-" + faultLine[1][4] + "\n")
    
    if(totalFaults != 0):
        outputFile.write("\nfault coverage: " + str(detectedFaults) + "/" + str(totalFaults) + " = " + "{:.0%}".format(detectedFaults/totalFaults))
    else:
        outputFile.write("\nfault coverage: 0/0 = 0%")
###########################----------------------------FAULT COVERAGE SECTION-------------------------------------##

    outputFile.close()
    #exit()


if __name__ == "__main__":
    main()

