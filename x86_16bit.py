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

def mov_encoder(operand_a,operand_b):
    retval = ''
    dest_reg = operand_a[1]
    if operand_b[0]=='LITERAL':
       retval = struct.pack('cch',chr(0x66),chr(dest_reg),operand_b[1])
    return retval

def push_encoder(operand):
    pass

def pop_encoder(operand):
    pass

assembler.add_opcode('MOV',[uniasm.Operand(from_reg=True,from_literal=False),
                            uniasm.Operand(from_reg=True,from_literal=True,from_mem=True,from_regptr=True,bitlength=16)],encoder_func=mov_encoder)


assembler.add_opcode('PUSH',[uniasm.Operand(from_reg=True,from_literal=True,bitlength=16)],encoder_func=push_encoder)

assembler.add_opcode('POP', [uniasm.Operand(from_reg=True,from_literal=False)],encoder_func=pop_encoder)

simple_code = """
    MOV AX, F33D
    MOV BX, FACE
    MOV CX, BEEF
    PUSH AX
    PUSH BX
    PUSH CX
    POP AX
    POP BX
    POP CX
"""

print assembler.verify(simple_code)
print hexlify(assembler.assemble_line('MOV AX, 1234'))
