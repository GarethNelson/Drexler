""" This does not attempt to implement a full usable x86 assembler for time reasons
"""
import uniasm
import struct
from binascii import hexlify

assembler = uniasm.Assembler()

assembler.add_reg('AX',0xB8,16)
assembler.add_reg('CX',0xB9,16)
assembler.add_reg('DX',0xBA,16)
assembler.add_reg('BX',0xBB,16)
assembler.add_reg('SP',0xBC,16)
assembler.add_reg('BP',0xBD,16)
assembler.add_reg('SI',0xBE,16)
assembler.add_reg('DI',0xBF,16)

def mov_encoder(asm,operand_a,operand_b):
    retval = ''
    dest_reg = operand_a[1]
    if operand_b[0]=='LITERAL':
       retval = struct.pack('ccH',chr(0x66),chr(dest_reg),operand_b[1])
    return retval


assembler.add_opcode('MOV',[uniasm.Operand(from_reg=True,from_literal=False),
                            uniasm.Operand(from_reg=True,from_literal=True,from_mem=True,from_regptr=True,bitlength=16)],encoder_func=mov_encoder)



src = """
    MOV AX, 0xF33D
    MOV BX, 0xFACE
    MOV CX, 0xBEEF
"""

verify_result = assembler.verify(src)
if not verify_result[0]:
   print 'Verification of source failed: %s' % verify_result[1]

output = assembler.compile(src)
if not output[0]:
   print 'Output generation failed: %s' % output[2]
   print 'Output to this point: \n %s' % hexlify(output[1])
else:
   print hexlify(output[1])


