import bitstring

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
   def add_reg(self,reg_name,reg_id,bitlength):
       self.known_register_id_codes[reg_name] = reg_id
       self.known_register_lengths[reg_name]  = bitlength
   def add_opcode(self,opcode_name,operands,encoder_func=None):
       self.known_opcodes_encoders[opcode_name] = encoder_func
       self.known_opcodes_operands[opcode_name] = operands
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
              parsed_operands.append(['VARIABLE',operand])
           else:
              parsed_operands.append(['LITERAL',int(operand)])
       return self.known_opcodes_encoders[raw_opcode](*parsed_operands)
   def compile(self,asm_src):
       """ Returns (True,binary) on success
           Returns (False,binary,err_msg) on failure - binary is the code compiled so far
       """
       bin_data = ''
       line_no = -1
       for line in asm_src.split('\n'):
           line_no += 1
           line = line.strip()
           if line.startswith(';'): continue
           if ':' in line:
              if count(':') >= 2: return (False,"Error on line %d: too many colon(:) tokens" % line_no)
              line = line.split(':')[1] # for labels etc
           if ';' in line:
              line = line.split(';')[0] # for comments
           if len(line) <= 2: continue
           split_line = line.split(' ')
           if not self.known_opcodes_operands.has_key(split_line[0]): return (False,bin_data,'Error on line %d: unknown opcode %s ' % (line_no,split_line[0]))
           try:
              bin_data += self.assemble_line(line)
           except Exception,e:
              return (False,bin_data,'Error on line %d: %s\n\t> %s' % (line_no,str(e),line))
       return (True,bin_data)     
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
              if count(':') >= 2: return (False,"Error on line %d: too many colon(:) tokens" % line_no)
              line = line.split(':')[1] # for labels etc
           if ';' in line:
              line = line.split(';')[0] # for comments
           if len(line) <= 2: continue
           split_line = line.split(' ')
           if not self.known_opcodes_operands.has_key(split_line[0]): return (False,'Error on line %d: unknown opcode %s ' % (line_no,split_line[0]))
       return (True,'OK')

