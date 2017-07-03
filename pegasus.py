import uniasm

assembler = uniasm.Assembler()

for x in xrange(0,16):
    assembler.add_reg('GPR%d' % x,x,32)

assembler.add_opcode('ADD',uniasm.Operand(from_reg=True,from_literal=False,bitlength=16),
                           uniasm.Operand(from_reg=True,from_literal=True,bitlength=16))

simple_addcode = """
   ADD GPR0 GPR1
   ADD GPR3 1337
"""

print assembler.verify(simple_addcode)
