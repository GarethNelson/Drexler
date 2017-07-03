; stupid simple kernel
; basically we setup all 3 tasks with their own mappings and have them spit out one of the letters A,B or C in a loop forever - which should result in ABCABCABCABC appearing on the console
; in the kernel's main loop we spit out "0" so it should actually be 0ABC0ABC0ABC etc

; we get loaded into bank 0 at startup, so first just copy ourselves into the other 3 physical banks up to the size of the kernel (by using the kernel_end symbol)
COPYBANK 0 1 $kernel_end
COPYBANK 0 2 $kernel_end
COPYBANK 0 3 $kernel_end

; map ourselves at bank 0 for every task but don't give the user tasks any permission to do anything with our memory (this is the default - permissions are default deny)
MAPBANK 1 0 0
MAPBANK 2 0 0
MAPBANK 3 0 0

; now we map virtual bank 1 to a different physical bank for each task
MAPBANK 1 1 1
MAPBANK 2 1 2
MAPBANK 3 1 3

; give permission to read,write and run from virtual bank 1 for each task
ALLOWMAPALL 1 1
ALLOWMAPALL 2 1
ALLOWMAPALL 3 1

; now setup syscall and exception handlers
SETSYSCALL   0 $syscall_handler
SETEXCEPTION 0 $exception_handler

; skip over the implementation of the 2 handlers defined above to our main loop init
JMPLOCAL $main_loop_init

; strings used for error messages
invalid_syscall_str: db "Invalid syscall ID!" ; a null-terminated string
                     db 0

syscall_handler:
		; we only actually have one type of syscall (0/write) so if it's not that, it's invalid
		EQ GPR0 0               ; if GPR0==0 then it's time to do a write
		JMPFAR 0 $syscall_write ; we need to use far jumps here because we don't know what state the CPU is in normally
		; if execution gets here, something went wrong so we spit out an error message and then break by using DEBUGSTR
		DEBUGSTR 0 $invalid_syscall_str
syscall_finish: ; this is the return for all syscalls and where the above DEBUGSTR will continue execution from
		SYSRET

syscall_write: 
		; implementation of the write syscall
		SETREG GPR3 1 ; needed for some arithmetic below
_write_loop:
		; basically, we check if GPR2 is 0, if not we write a single byte, then decrement GPR2 and loop back here
		; otherwise we're done, so we just go to syscall_finish above
		NOTZERO GPR2
		JMPFAR 0 $_write_one_char
		JMPFAR 0 $syscall_finish

_write_one_char:
		; and here we just write a single character and then go back to the loop
		WRITEBYTE 0 REGPTR:GPR1 ; we use register pointer mode to pass the operand for the WRITEBYTE instruction
		SUB GPR2 GPR3 ; subtract 1 from GPR2, store result in GPR2
		ADD GPR1 GPR3 ; add 1 to GPR1 in case we need to write the next byte
		JMPFAR 0 $_write_loop ; go back to the loop (which will then check if GPR2 is 0, and if not, will return here)

exception_handler:
		BREAK ; we should do more here, but this helps debugging - since exception handlers always run in privileged mode, the BREAK instruction here will cause a full system halt
		      ; in emulation, this should go into single-step debug mode

; main loop init (set stuff up and enable tasks first)
main_loop_init:
		; first we setup GPR0 for each task to the ASCII value for the letter A, B or C
		SETREG T1GPR0 65
		SETREG T2GPR0 66
		SETREG T3GPR0 67

		; then we setup the bank register (set it to 1)
                SETREG T1BANK 1
                SETREG T2BANK 1
                SETREG T3BANK 1
		
		; the default IP for all tasks is IP0, which in our case would mean attempting to run privileged code and fucking stuff up
		; so let's set the IP for each task to point to the unprivileged code
                SETREG T1IP $user_code
                SETREG T2IP $user_code
                SETREG T3IP $user_code

		ENABLETASK 1
		ENABLETASK 2
		ENABLETASK 3

; our kernel main loop
main_loop:
		; write out the ASCII character "0" to the console so we know when the kernel is running this main loop
		WRITEBYTE 0 48

		JMPLOCAL $main_loop ; jump back to the main loop

; some reserved space lives here
user_task_char: db 0 ; reserve a single byte

; here is where our unprivileged code lives - in a proper system this should be in another file
user_code:
		USEBANK 1 ; although we don't need to do this, it's good practice to be sure we're in the correct bank

		; to test that we actually are in a different bank, we copy from GPR0 to the reserved memory address above
		; the below instruction uses register value mode
		SETMEM8 $user_task_char GPR0

user_code_loop:
		; now we use the syscall to write our byte out to the console in a loop
		SETREG GPR0 0               ; GPR0 is used to indicate which syscall we want, in this case it's write
		SETREG GPR1 $user_task_char ; GPR1 is used to indicate what we want to write as a memory address - note that this is NOT an indirect value, it's a literal
		SETREG GPR2 1               ; GPR2 is used to indicate the length of the string we want to write - here it's only 1 byte long
		SYSCALL                     ; finally, we run the syscall
		JMPLOCAL $user_code_loop    ; and then we loop back forever

; this symbol is used to calculate the size of the kernel for copying
kernel_end:
