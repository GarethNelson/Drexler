import bitstring
import binascii

def assemble_bits(*bits):
    """ Utility function to turn a string of bits into a string of bytes
    """
    retval = bitstring.BitArray()
    for b in bits:
        retval.append(bitstring.BitArray(bin=b))
    return retval.tobytes()

class Operand:
   def __init__(self,from_reg=False,from_literal=False,from_mem=False,from_regptr=False,bitlength=8):
       """ from_reg -     allow setting this operand from a register
           from_literal - allow setting this operand from a literal value
           from_mem     - allow setting this operand from a memory address (can also use $ notation to point to a label)
           from_regptr  - allow setting this operand from a memory address specified by a register (for example mov ax.[di] to set ax to the value at memory address stored in di register)
           bitlength    - the bitlength of this operand for literal values
       """
       self.from_mem     = from_mem
       self.from_regptr  = from_regptr
       self.from_reg     = from_reg
       self.from_literal = from_literal
       self.bitlength    = bitlength

class Assembler:
   def __init__(self):
       self.known_opcodes_operands  = {}
       self.known_opcodes_encoders  = {}
       self.known_register_lengths  = {}
       self.known_register_id_codes = {}
       self.substitute_vars         = {}
       self.bin_cleanups            = []
       self.bin_data                = ''
   def add_reg(self,reg_name,reg_id,bitlength):
       self.known_register_id_codes[reg_name] = reg_id
       self.known_register_lengths[reg_name]  = bitlength
   def add_opcode(self,opcode_name,operands,encoder_func=None):
       self.known_opcodes_encoders[opcode_name] = encoder_func
       self.known_opcodes_operands[opcode_name] = operands
   def add_cleanup(self,offset,var,bitlen=16):
       """ While assembling, use this to add offsets that need to be replaced with the value of variable var after done
       """
       self.bin_cleanups.append([offset,var,bitlen])
   def assemble_line(self,line):
       """ Assemble a single line, already processed for things like $ values etc
           Must have only opcode and operands: operands may be literals, registers or whatever is allowed
       """
       split_line = line.split()
       raw_opcode   = split_line[0]
       raw_operands = split_line[1:]
       if self.known_opcodes_encoders[raw_opcode] is None:
          retval = None
          return retval
       parsed_operands = []
       for operand in raw_operands:
           operand = operand.strip(',')
           if self.known_register_id_codes.has_key(operand):
              parsed_operands.append(['REG',self.known_register_id_codes[operand]])
           elif operand.startswith('$'):
              parsed_operands.append(['VARIABLE',operand[1:]])
           else:
              if operand.startswith('0x'):
                 parsed_operands.append(['LITERAL',int(operand[2:],16)])
              else:
                 parsed_operands.append(['LITERAL',int(operand)])
       return self.known_opcodes_encoders[raw_opcode](self,*parsed_operands)
   def find_var(self,var):
       """ Returns either the variable offset for var or None
           If None is returned, the variable has not yet been defined
           In this case, a placeholder value should be assembled and an entry added to cleanups via add_cleanup()
       """
       if not self.substitute_vars.has_key(var): return None
       return self.substitute_vars[var]
   def compile(self,asm_src):
       """ Returns (True,binary) on success
           Returns (False,binary,err_msg) on failure - binary is the code compiled so far
       """
       self.substitute_vars = {}
       self.bin_cleanups    = []
       self.bin_data = ''
       line_no = -1
       for line in asm_src.split('\n'):
           line_no += 1
           line = line.strip()
           if line.startswith(';'): continue
           if ':' in line:
              if line.count(':') >= 2: return (False,"Error on line %d: too many colon(:) tokens" % line_no)
              self.substitute_vars[line.split(':')[0]] = len(self.bin_data) # len(bin_data) is equivalent to the offset of the code at this point in the source
              line = line.split(':')[1] # for labels etc

           if ';' in line:
              line = line.split(';')[0] # for comments
           if len(line) <= 2: continue
           split_line = line.split(' ')
           if not self.known_opcodes_operands.has_key(split_line[0]): return (False,self.bin_data,'Error on line %d: unknown opcode %s ' % (line_no,split_line[0]))
           try:
              self.bin_data += self.assemble_line(line)
           except Exception,e:
              return (False,self.bin_data,'Error on line %d: %s\n\t> %s' % (line_no,str(e),line))
       for cleanup in self.bin_cleanups:
           if self.find_var(cleanup[1]) is None: return (False,self.bin_data,'Error during variable resolution: no such symbol %s' % cleanup[1])
           data_bits = bitstring.BitArray(bytes=self.bin_data)
           var_bits  = bitstring.BitArray(bin=format(self.find_var(cleanup[1]),'#018b'))
           data_bits.overwrite(var_bits,cleanup[0]*8)
           self.bin_data = data_bits.tobytes()
       return (True,self.bin_data)
   def verify(self,asm_src):
       """ Returns (True,'OK') on success
           Returns (False,err_msg) on failure
       """
       line_no = -1
       for line in asm_src.split('\n'):
           line_no += 1
           line = line.strip()
           if line.startswith(';'): continue
           if ':' in line:
              if line.count(':') >= 2: return (False,"Error on line %d: too many colon(:) tokens" % line_no)
              line = line.split(':')[1] # for labels etc
           if ';' in line:
              line = line.split(';')[0] # for comments
           if len(line) <= 2: continue
           split_line = line.split(' ')
           if not self.known_opcodes_operands.has_key(split_line[0]): return (False,'Error on line %d: unknown opcode %s ' % (line_no,split_line[0]))
       return (True,'OK')

