class Operand:
   def __init__(self,from_reg=False,from_literal=False,bitlength=8):
       """ from_reg -     allow setting this operand from a register
           from_literal - allow setting this operand from a literal value
           bitlength    - the bitlength of this operand for literal values
       """
       self.from_reg     = from_reg
       self.from_literal = from_literal
       self.bitlength    = bitlength

class Assembler:
   def __init__(self):
       self.known_opcodes_operands  = {}
       self.known_register_lengths  = {}
       self.known_register_id_codes = {}
   def add_reg(self,reg_name,reg_id,bitlength):
       self.known_register_id_codes[reg_name] = reg_id
       self.known_register_lengths[reg_name]  = bitlength
   def add_opcode(self,opcode_name,*operands):
       self.known_opcodes_operands[opcode_name] = operands
   def verify(self,asm_src):
       """ Returns (True,'OK') on success
           Returns (False,err_msg) on failure
       """
       line_no = 0
       for line in asm_src.split('\n'):
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
