import sys
import uniasm
from binascii import hexlify

assembler = uniasm.Assembler()

REGISTER_CTX_GLOBAL  = '000'
REGISTER_CTX_CURRENT = '001'
REGISTER_CTX_TASK0   = '010'
REGISTER_CTX_TASK1   = '011'
REGISTER_CTX_TASK2   = '100'
REGISTER_CTX_TASK3   = '101'

REGISTER_TYPE_STATUS   = '00'
REGISTER_TYPE_LOCALGPR   = '01'
REGISTER_TYPE_GLOBALEXC  = '01'
REGISTER_TYPE_LOCALMMAP     = '10'
REGISTER_TYPE_GLOBALSYSCALL = '10'
REGISTER_TYPE_LOCAL_IOMAP = '11'

REGISTER_SPEC0 = '000'
REGISTER_SPEC1 = '001'
REGISTER_SPEC2 = '010'
REGISTER_SPEC3 = '011'
REGISTER_SPEC4 = '100'
REGISTER_SPEC5 = '101'
REGISTER_SPEC6 = '110'
REGISTER_SPEC7 = '111'

OPCODE_REGLOAD  = 0x01
OPCODE_REGSAVE  = 0x02
OPCODE_COPYBANK = 0x03
OPCODE_JMPLOCAL = 0x04

def make_regid(reg_ctx,reg_type,reg_specific):
    retval = '0b%s%s%s' % (reg_ctx,reg_type,reg_specific)
    return int(retval,2)

# setup global registers first
assembler.add_reg('GSTATUS',  make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_STATUS,REGISTER_SPEC0),32)    # global status
assembler.add_reg('EXCEPTION',make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALEXC,REGISTER_SPEC0),32) # exception handler
assembler.add_reg('SYSCALL',  make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALSYSCALL,REGISTER_SPEC0),32)   # syscall handler

# now setup per task registers
for task in [('',REGISTER_CTX_CURRENT),('T0',REGISTER_CTX_TASK0,),('T1',REGISTER_CTX_TASK1),('T2',REGISTER_CTX_TASK2),('T3',REGISTER_CTX_TASK3)]:
    assembler.add_reg('%sSTATUS' % task[0],make_regid(task[1],REGISTER_TYPE_STATUS,REGISTER_SPEC0),32)
    assembler.add_reg('%sBANK'   % task[0],make_regid(task[1],REGISTER_TYPE_STATUS,REGISTER_SPEC0),32) # virtual register
    assembler.add_reg('%sIP'     % task[0],make_regid(task[1],REGISTER_TYPE_STATUS,REGISTER_SPEC0),32) # virtual register
    for reg_type in [('GPR',REGISTER_TYPE_LOCALGPR),('MMAP',REGISTER_TYPE_LOCALMMAP),('IOMAP',REGISTER_TYPE_LOCAL_IOMAP)]:
        assembler.add_reg('%s%s0' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC0),32)
        assembler.add_reg('%s%s1' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC1),32)
        assembler.add_reg('%s%s2' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC2),32)
        assembler.add_reg('%s%s3' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC3),32)
        assembler.add_reg('%s%s4' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC4),32)
        assembler.add_reg('%s%s5' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC5),32)
        assembler.add_reg('%s%s6' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC6),32)
        assembler.add_reg('%s%s7' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC7),32)

def encode_copybank(asm,src_bank,dst_bank,offset):
    retval  = ''
    retval += chr(OPCODE_COPYBANK)
    src_bits = format(src_bank[1], '#004b')
    dst_bits = format(dst_bank[1], '#004b')
    if offset[0]=='LITERAL':
       offset_bits = format(offset[1], '#016b')
    elif offset[0]=='VARIABLE':
       var_val = asm.find_var(offset[1])
       if var_val == None:
          asm.add_cleanup(len(asm.bin_data)+2,offset[1])
          offset_bits = format(0xBEEF, '#016b')
       else:
          offset_bits = format(int(var_val), '#016b')
    retval += uniasm.assemble_bits(src_bits,dst_bits,offset_bits)
    return retval

def encode_mapbank(asm,task_id,virtual_bank,physical_bank):
    # this is not actually a real opcode, it's OPCODE_REGSAVE so we can assign stuff in global registers
    # basically to do a MAPBANK we just update the mmap register for the specific task
    reg_ctx = {0:REGISTER_CTX_TASK0,
               1:REGISTER_CTX_TASK1,
               2:REGISTER_CTX_TASK2,
               3:REGISTER_CTX_TASK3}[task_id[1]]
    reg_id = make_regid(reg_ctx,REGISTER_TYPE_LOCALMMAP,virtual_bank[1])

    # now we need to assemble the new contents for the mmap register - see pegasus_docs/new_isa.txt
    new_mmap = uniasm.assemble_bits('0'*16,                        # 16-bits reserved
                                    '0'*4,                         # 4 bits reserved
                                    '0001',                        # default permissions 0 on all, but bank present
                                     format(physical_bank[1],'#008b')) # physical bank
   
    # now let's assemble the actual code
    retval  = ''
    retval += chr(OPCODE_REGLOAD)
    retval += uniasm.assemble_bits(format(reg_id,'#008b'),   # register ID
                                   '00',                     # overwrite and do not zero extend
                                   '000',                    # set whole register
                                   '010')                    # set from literal 32-bit
    retval += new_mmap # the new mmap value
    return retval

def encode_allowmapall(asm,task_id,virtual_bank):
    # this is not actually a real opcode, it's OPCODE_REGSAVE so we can assign stuff in global registers
    # basically to do a MAPBANK we just update the mmap register for the specific task
    reg_ctx = {0:REGISTER_CTX_TASK0,
               1:REGISTER_CTX_TASK1,
               2:REGISTER_CTX_TASK2,
               3:REGISTER_CTX_TASK3}[task_id[1]]
    reg_id = make_regid(reg_ctx,REGISTER_TYPE_LOCALMMAP,virtual_bank[1])

    # now we need to assemble the new contents for the mmap register - see pegasus_docs/new_isa.txt
    # we OR write it to the register, so anything we're not changing below must be 0
    new_mmap = uniasm.assemble_bits('0'*16,                        # 16-bits reserved
                                    '0'*4,                         # 4 bits reserved
                                    '1110',                        # set all permissions
                                     '0'*4)                        # physical bank
   
    # now let's assemble the actual code
    retval  = ''
    retval += chr(OPCODE_REGLOAD)
    retval += uniasm.assemble_bits(format(reg_id,'#008b'),   # register ID
                                   '10',                     # OR write and do not zero extend
                                   '000',                    # set whole register
                                   '010')                    # set from literal 32-bit
    retval += new_mmap # the new mmap value
    return retval

def encode_setsyscall(asm,bank,offset):
    # this is another virtual opcode implemented using REGSAVE
    reg_id = make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALSYSCALL,REGISTER_SPEC0)
    if offset[0]=='LITERAL':
       new_syscall_reg = uniasm.assemble_bits('0'*8,                     # 8 bit syscall ID - blank by default for obvious reasons
                                              format(bank[1],'#008b'),   # 8 bit physical bank ID
                                              format(offset[1],'#016b')) # 16-bit memory offset
    elif offset[0]=='VARIABLE':
       new_syscall_reg = uniasm.assemble_bits('0'*8,                     # 8 bit syscall ID - blank by default for obvious reasons
                                              format(bank[1],'#008b'),   # 8 bit physical bank ID
                                              format(0xBEEF,'#016b')) # 16-bit memory offset
       asm.add_cleanup(len(asm.bin_data)+2,offset[1])
    retval  = ''
    retval += chr(OPCODE_REGLOAD)
    retval += uniasm.assemble_bits(format(reg_id,'#008b'),   # register ID
                                   '10',                     # OR write and do not zero extend
                                   '000',                    # set whole register
                                   '010')                    # set from literal 32-bit
    retval += new_syscall_reg # the new value
    return retval


def encode_setexception(asm,bank,offset):
    # this is another virtual opcode implemented using REGSAVE
    reg_id = make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALEXC,REGISTER_SPEC0)
    if offset[0]=='LITERAL':
       new_exc_reg = uniasm.assemble_bits('0'*8,                     # 8 bit syscall ID - blank by default for obvious reasons
                                              format(bank[1],'#008b'),   # 8 bit physical bank ID
                                              format(offset[1],'#016b')) # 16-bit memory offset
    elif offset[0]=='VARIABLE':
       new_exc_reg = uniasm.assemble_bits('0'*8,                     # 8 bit syscall ID - blank by default for obvious reasons
                                              format(bank[1],'#008b'),   # 8 bit physical bank ID
                                              format(0xBEEF,'#016b')) # 16-bit memory offset
       asm.add_cleanup(len(asm.bin_data)+2,offset[1])
    retval  = ''
    retval += chr(OPCODE_REGLOAD)
    retval += uniasm.assemble_bits(format(reg_id,'#008b'),   # register ID
                                   '10',                     # OR write and do not zero extend
                                   '000',                    # set whole register
                                   '010')                    # set from literal 32-bit
    retval += new_exc_reg # the new value
    return retval

def encode_jmplocal(asm,offset):
    retval  = ''
    retval += chr(OPCODE_JMPLOCAL)
    if offset[0]=='LITERAL':
       retval += uniasm.assemble_bits(format(offset[1],'#016b'))
    elif offset[0]=='VARIABLE':
       retval += uniasm.assemble_bits(format(0xBEEF,'#016b'))
       asm.add_cleanup(len(asm.bin_data)+1,offset[1])
    return retval

# read pegassus_docs/instruction_set.txt for details on this stuff

assembler.add_opcode('COPYBANK',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),   # source bank
                                 uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),   # destination bank
                                 uniasm.Operand(from_reg=False,from_literal=True,bitlength=16)], # address offset
                                 encoder_func=encode_copybank)

assembler.add_opcode('MAPBANK',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),    # which task are we messing with?
                                uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),    # which virtual bank are we setting up?
                                uniasm.Operand(from_reg=False,from_literal=True,bitlength=8)],   # which physical bank do we want to assign to it?
                                encoder_func=encode_mapbank)

assembler.add_opcode('ALLOWMAPALL',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=4), # which task?
                                    uniasm.Operand(from_reg=False,from_literal=True,bitlength=4)], # which virtual bank?
                                    encoder_func=encode_allowmapall)

assembler.add_opcode('SETSYSCALL',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=8),   # which physical bank?
                                   uniasm.Operand(from_reg=False,from_literal=True,bitlength=16)], # which memory offset?
                                   encoder_func=encode_setsyscall)

assembler.add_opcode('SETEXCEPTION',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=8),   # which physical bank?
                                     uniasm.Operand(from_reg=False,from_literal=True,bitlength=16)], # which memory offset?
                                     encoder_func=encode_setexception)

assembler.add_opcode('JMPLOCAL',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=16)],
                                 encoder_func=encode_jmplocal)

def do_line(l):
    print '"%s"  =>  0x%s' % (l,hexlify(assembler.assemble_line(l)))

#do_line('COPYBANK 0 1 20')
#do_line('MAPBANK  0 0 1')


if len(sys.argv)==2:
   fd = open(sys.argv[1],'r')
   src = fd.read()
   fd.close()
   verify_result = assembler.verify(src)
   if not verify_result[0]:
      print 'Verification of source failed: %s' % verify_result[1]
 
   output = assembler.compile(src)
   if not output[0]:
      print 'Output generation failed: %s' % output[2]
      print 'Output to this point: \n %s' % hexlify(output[1])
   else:
      print hexlify(output[1])
