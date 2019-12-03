def main():


    f= open("LUT.bench","w+")
    print("Number of inputs: ")
    inC=int(input())
    print("Circuit Output (y0 y1...yn)")
    outC=input()

    var=0
    while (var<inC):
        f.write("INPUT("+str(var)+")\n")
        var=var+1

    muxC=(2**inC)-1
    f.write("\nOUTPUT("+str((muxC+inC))+")\n")

    i=0
    while (i<len(outC)):
        f.write(str(var)+ "=MUX("+ outC[i]+", "+outC[i+1]+", 0)\n")
        i=i+2
        var=var+1
        muxC=muxC-1


    j=0
    while (j <= muxC):
        f.write(str(var)+ "=MUX("+ str(var-2) +", "+ str(var-1) +", 0)\n")
        j=j+1
        var=var+1
        muxC=muxC-1
        print("mux left: " + str(muxC))























    f.close()




if __name__ == "__main__":
    main()
